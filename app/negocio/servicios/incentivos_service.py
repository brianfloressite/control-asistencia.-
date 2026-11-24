"""Módulo de Liquidación de Bonos y Gestión Disciplinaria: reglas (CU10), bono (CU11) y medidas (CU12)."""
import calendar
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from flask import current_app
from app.datos import modelos as m
from app.datos.repositorios import (ReglaRepositorio, LiquidacionRepositorio, ColaboradorRepositorio, InconsistenciaRepositorio,
                                    MarcaRepositorio, AlertaRepositorio, MedidaRepositorio)
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.seguridad_service import BitacoraService
from app.negocio.servicios.auditoria_service import AsistenciaService

TIPOS_MEDIDA = {"AMONESTACION_VERBAL": "Amonestación verbal", "AMONESTACION_ESCRITA": "Amonestación escrita",
                "SUSPENSION": "Suspensión", "CESE": "Cese"}


def rango_mes(anio, mes):
    return date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])


class ReglaService:
    @staticmethod
    def vigente():
        return ReglaRepositorio.vigente()

    @staticmethod
    def historial():
        return ReglaRepositorio.historial()

    @staticmethod
    def actualizar(datos, actor, ip=None):
        """Crea una nueva versión de reglas; la anterior queda cerrada (Strategy configurable por vigencia)."""
        try:
            monto = Decimal(str(datos.get("monto_bono")))
            valores = {k: int(datos.get(k)) for k in ("tolerancia_min", "max_tardanzas_bono", "tardanzas_alerta", "faltas_alerta")}
            vigencia = datetime.strptime(datos.get("vigencia_desde"), "%Y-%m-%d").date()
        except (TypeError, ValueError, InvalidOperation):
            raise ErrorNegocio("Revise los valores: deben ser números válidos y la fecha de vigencia es obligatoria.")
        if monto <= 0 or valores["tardanzas_alerta"] <= 0 or valores["faltas_alerta"] <= 0:
            raise ErrorNegocio("El monto del bono y los umbrales de alerta deben ser mayores a 0.")
        if valores["tolerancia_min"] < 0 or valores["max_tardanzas_bono"] < 0:
            raise ErrorNegocio("La tolerancia y el máximo de tardanzas no pueden ser negativos.")
        for r in ReglaRepositorio.listar(vigente=True):
            r.vigente = False
        regla = m.ReglaNegocio(monto_bono=monto, vigencia_desde=vigencia, vigente=True, id_usuario=actor.id_usuario, **valores)
        ReglaRepositorio.agregar(regla)
        BitacoraService.registrar(actor.id_usuario, "ACTUALIZAR", "Reglas", f"Nueva versión desde {vigencia} (bono S/ {monto})", ip, commit=False)
        ReglaRepositorio.guardar()
        return regla


class BonoService:
    @staticmethod
    def evaluar(conteo, regla):
        """Regla del bono: tardanzas ≤ máximo permitido y sin faltas ni abandonos (función pura)."""
        apto = conteo.get("TARDANZA", 0) <= regla.max_tardanzas_bono and conteo.get("FALTA", 0) == 0 and conteo.get("ABANDONO", 0) == 0
        return apto, (Decimal(regla.monto_bono) if apto else Decimal("0.00"))

    @classmethod
    def calcular(cls, anio, mes, actor, id_area=None, ip=None):
        desde, hasta = rango_mes(anio, mes)
        existente = LiquidacionRepositorio.por_periodo(anio, mes)
        if existente and existente.estado == "CERRADA":
            return existente, ["El periodo ya fue liquidado: se muestra la liquidación existente."]
        regla = ReglaRepositorio.vigente(hasta)
        if regla is None:
            raise ErrorNegocio("Configure primero las reglas de negocio (CU10).")
        avisos = []
        pendientes = MarcaRepositorio.contar_pendientes_periodo(desde, hasta)
        if pendientes:
            avisos.append(f"Existen {pendientes} marca(s) de contingencia pendientes: la liquidación solo puede guardarse como borrador.")
        AsistenciaService.detectar(desde, hasta, id_area)
        liq = existente or m.LiquidacionBono(anio=anio, mes=mes)
        liq.id_regla, liq.id_usuario, liq.estado = regla.id_regla, actor.id_usuario, "BORRADOR"
        liq.detalles.clear()
        if existente is None:
            LiquidacionRepositorio.agregar(liq)
        for c in ColaboradorRepositorio.activos(id_area):
            conteo = InconsistenciaRepositorio.conteo_por_tipo(c.id_colaborador, desde, hasta)
            apto, monto = cls.evaluar(conteo, regla)
            liq.detalles.append(m.BonoDetalle(id_colaborador=c.id_colaborador, tardanzas=conteo.get("TARDANZA", 0),
                                              faltas=conteo.get("FALTA", 0), abandonos=conteo.get("ABANDONO", 0), apto=apto, monto=monto))
        BitacoraService.registrar(actor.id_usuario, "CALCULAR", "Bonos", f"Bono {mes:02d}/{anio}", ip, commit=False)
        LiquidacionRepositorio.guardar()
        return liq, avisos

    @staticmethod
    def cerrar(id_liquidacion, actor, ip=None):
        liq = LiquidacionRepositorio.obtener(id_liquidacion)
        if liq is None:
            raise ErrorNegocio("Liquidación no encontrada.")
        desde, hasta = rango_mes(liq.anio, liq.mes)
        if MarcaRepositorio.contar_pendientes_periodo(desde, hasta):
            raise ErrorNegocio("No se puede cerrar: hay marcas de contingencia pendientes de validar.")
        liq.estado, liq.fecha_cierre = "CERRADA", datetime.now()
        BitacoraService.registrar(actor.id_usuario, "CERRAR", "Bonos", f"Liquidación {liq.mes:02d}/{liq.anio}", ip, commit=False)
        LiquidacionRepositorio.guardar()
        return liq


class DisciplinaService:
    @staticmethod
    def generar_alertas(hoy=None):
        hoy = hoy or date.today()
        regla = ReglaRepositorio.vigente(hoy)
        if regla is None:
            return 0
        desde, hasta = rango_mes(hoy.year, hoy.month)
        AsistenciaService.detectar(desde, min(hasta, hoy))
        n = 0
        for c in ColaboradorRepositorio.activos():
            conteo = InconsistenciaRepositorio.conteo_por_tipo(c.id_colaborador, desde, hasta)
            for tipo, clave, umbral in (("TARDANZAS", "TARDANZA", regla.tardanzas_alerta), ("FALTAS", "FALTA", regla.faltas_alerta)):
                cant = conteo.get(clave, 0)
                if cant >= umbral and AlertaRepositorio.activa_de(c.id_colaborador, tipo) is None:
                    AlertaRepositorio.agregar(m.AlertaDisciplinaria(id_colaborador=c.id_colaborador, id_regla=regla.id_regla, tipo=tipo,
                                                                    cantidad=cant, fecha_generacion=hoy))
                    n += 1
        AlertaRepositorio.guardar()
        return n

    @staticmethod
    def alertas():
        return AlertaRepositorio.activas()

    @staticmethod
    def medidas():
        return MedidaRepositorio.recientes()

    @classmethod
    def registrar_medida(cls, id_alerta, tipo, sustento, emitir_pdf, actor, ip=None):
        alerta = AlertaRepositorio.obtener(id_alerta)
        if alerta is None or alerta.estado != "ACTIVA":
            raise ErrorNegocio("Seleccione una alerta activa.")
        if tipo not in TIPOS_MEDIDA:
            raise ErrorNegocio("Seleccione el tipo de medida.")
        if len((sustento or "").strip()) < 10:
            raise ErrorNegocio("Escriba el sustento de la medida (mínimo 10 caracteres).")
        medida = m.MedidaDisciplinaria(id_alerta=alerta.id_alerta, id_colaborador=alerta.id_colaborador, id_usuario=actor.id_usuario,
                                       tipo=tipo, sustento=sustento.strip(), fecha=date.today())
        MedidaRepositorio.agregar(medida)
        alerta.estado = "ATENDIDA"
        MedidaRepositorio.guardar()
        if emitir_pdf:
            medida.ruta_carta_pdf = cls.generar_carta(medida)
        BitacoraService.registrar(actor.id_usuario, "SANCIONAR", "Disciplina", f"{TIPOS_MEDIDA[tipo]} a {alerta.colaborador.dni}", ip, commit=False)
        MedidaRepositorio.guardar()
        return medida

    @staticmethod
    def descartar(id_alerta, motivo, actor, ip=None):
        alerta = AlertaRepositorio.obtener(id_alerta)
        if alerta is None or not (motivo or "").strip():
            raise ErrorNegocio("Indique el motivo para descartar la alerta.")
        alerta.estado, alerta.motivo_descarte = "DESCARTADA", motivo.strip()[:255]
        BitacoraService.registrar(actor.id_usuario, "DESCARTAR", "Disciplina", f"Alerta #{alerta.id_alerta}", ip, commit=False)
        AlertaRepositorio.guardar()

    @staticmethod
    def generar_carta(medida):
        """Genera la carta de amonestación en PDF con ReportLab."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        carpeta = current_app.config["ARCHIVOS_DIR"]
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"carta_medida_{medida.id_medida}.pdf")
        c, est = medida.colaborador, getSampleStyleSheet()
        doc = SimpleDocTemplate(ruta, pagesize=A4)
        doc.build([Paragraph("FUNERARIA DEL CASTILLO", est["Title"]), Paragraph(f"Lima, {medida.fecha:%d/%m/%Y}", est["Normal"]), Spacer(1, 16),
                   Paragraph(f"Señor(a): {c.nombres} {c.apellidos} — DNI {c.dni}", est["Normal"]), Spacer(1, 12),
                   Paragraph(f"Asunto: {TIPOS_MEDIDA[medida.tipo]}", est["Heading3"]),
                   Paragraph(medida.sustento.replace("\n", "<br/>"), est["Normal"]), Spacer(1, 40),
                   Paragraph("Jefatura de Recursos Humanos", est["Normal"])])
        return ruta
