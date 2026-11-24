"""Módulo de Reportes Gerenciales y Dashboard: historial (CU13), dashboard (CU14) y exportación (CU15)."""
import io
from datetime import date, timedelta
from app.datos import modelos as m
from app.datos.repositorios import (MarcaRepositorio, InconsistenciaRepositorio, LiquidacionRepositorio, ColaboradorRepositorio,
                                    TurnoRepositorio, MedidaRepositorio, AreaRepositorio, SincronizacionRepositorio)
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.seguridad_service import BitacoraService
from app.negocio.servicios.auditoria_service import AsistenciaService
from app.negocio.servicios.incentivos_service import rango_mes, TIPOS_MEDIDA


class HistorialService:
    @staticmethod
    def de_colaborador(colaborador, desde, hasta):
        if colaborador is None:
            raise ErrorNegocio("Su usuario no está asociado a un colaborador.")
        if desde > hasta:
            raise ErrorNegocio("La fecha de inicio no puede ser posterior a la fecha de fin.")
        AsistenciaService.detectar(desde, hasta)
        marcas = MarcaRepositorio.del_colaborador(colaborador.id_colaborador, desde, hasta)
        incs = InconsistenciaRepositorio.buscar(desde, hasta, id_colaborador=colaborador.id_colaborador)
        dias = sorted({mk.fecha_hora.date() for mk in marcas if mk.estado != "RECHAZADA"})
        resumen = {"dias": len(dias), "tardanzas": sum(1 for i in incs if i.tipo == "TARDANZA" and i.estado != "JUSTIFICADA"),
                   "faltas": sum(1 for i in incs if i.tipo == "FALTA" and i.estado != "JUSTIFICADA")}
        bonos = LiquidacionRepositorio.bonos_del_colaborador(colaborador.id_colaborador)
        return {"marcas": marcas, "inconsistencias": incs, "resumen": resumen, "bonos": bonos}


class DashboardService:
    @staticmethod
    def indicadores(anio, mes, id_area=None):
        desde, hasta = rango_mes(anio, mes)
        hasta_eval = min(hasta, date.today())
        if desde > hasta_eval:
            return {"puntualidad": 0, "ausentismo": 0, "guardias": 0, "bonos": 0, "medidas": 0, "semanas": [], "areas": [], "sin_datos": True}
        AsistenciaService.detectar(desde, hasta_eval, id_area)
        turnos = TurnoRepositorio.en_rango(desde, hasta_eval, id_area)
        programados = guardias = 0
        for t in turnos:
            n = (min(t.fecha_fin, hasta_eval) - max(t.fecha_inicio, desde)).days + 1
            programados += max(n, 0)
            if t.horario.es_guardia_24h:
                guardias += max(n, 0)
        incs = InconsistenciaRepositorio.buscar(desde, hasta_eval, id_area)
        incs = [i for i in incs if i.estado != "JUSTIFICADA"]
        faltas = sum(1 for i in incs if i.tipo == "FALTA")
        tard = sum(1 for i in incs if i.tipo == "TARDANZA")
        aband = sum(1 for i in incs if i.tipo == "ABANDONO" and i.turno.horario.es_guardia_24h)
        asistidos = max(programados - faltas, 0)
        liq = LiquidacionRepositorio.por_periodo(anio, mes)
        semanas = []
        inicio = desde
        while inicio <= hasta_eval:
            fin = min(inicio + timedelta(days=6), hasta_eval)
            t_sem = sum(1 for i in incs if i.tipo == "TARDANZA" and inicio <= i.fecha <= fin)
            prog_sem = sum(max((min(t.fecha_fin, fin) - max(t.fecha_inicio, inicio)).days + 1, 0) for t in turnos)
            f_sem = sum(1 for i in incs if i.tipo == "FALTA" and inicio <= i.fecha <= fin)
            asis = max(prog_sem - f_sem, 0)
            semanas.append({"etiqueta": f"{inicio:%d/%m}", "puntualidad": round(100 * (asis - t_sem) / asis, 1) if asis else 0})
            inicio = fin + timedelta(days=1)
        areas = []
        for a in AreaRepositorio.listar(estado=True):
            if id_area and a.id_area != id_area:
                continue
            f_a = sum(1 for i in incs if i.tipo == "FALTA" and i.colaborador.id_area == a.id_area)
            p_a = sum(max((min(t.fecha_fin, hasta_eval) - max(t.fecha_inicio, desde)).days + 1, 0) for t in turnos if t.colaborador.id_area == a.id_area)
            areas.append({"area": a.nombre, "ausentismo": round(100 * f_a / p_a, 1) if p_a else 0})
        return {
            "puntualidad": round(100 * (asistidos - tard) / asistidos, 1) if asistidos else 0,
            "ausentismo": round(100 * faltas / programados, 1) if programados else 0,
            "guardias": round(100 * (guardias - aband) / guardias, 1) if guardias else 100,
            "bonos": sum(1 for d in liq.detalles if d.apto) if liq else 0,
            "medidas": MedidaRepositorio.activas_count(), "semanas": semanas, "areas": areas, "sin_datos": programados == 0,
            "marcas_hoy": MarcaRepositorio.contar_dia(date.today()),
        }


class ReporteService:
    TIPOS = {"asistencia": "Reporte de asistencia", "bonos": "Reporte de bonos de puntualidad", "sanciones": "Reporte de sanciones"}

    @staticmethod
    def datos(tipo, desde, hasta, id_area=None, id_colaborador=None):
        if desde > hasta:
            raise ErrorNegocio("La fecha de inicio no puede ser posterior a la fecha de fin.")
        if tipo == "asistencia":
            AsistenciaService.detectar(desde, hasta, id_area)
            cab = ["Colaborador", "DNI", "Área", "Fecha", "Tipo", "Minutos", "Estado"]
            filas = [[i.colaborador.nombre_completo, i.colaborador.dni, i.colaborador.area.nombre, i.fecha.strftime("%d/%m/%Y"),
                      i.tipo.title(), i.minutos, i.estado.replace("_", " ").title()]
                     for i in InconsistenciaRepositorio.buscar(desde, hasta, id_area, id_colaborador=id_colaborador)]
        elif tipo == "bonos":
            cab = ["Periodo", "Colaborador", "Tardanzas", "Faltas", "Abandonos", "Resultado", "Monto (S/)"]
            filas = []
            for liq in m.LiquidacionBono.query.all():
                if not (desde <= rango_mes(liq.anio, liq.mes)[1] and rango_mes(liq.anio, liq.mes)[0] <= hasta):
                    continue
                for d in liq.detalles:
                    if (id_area and d.colaborador.id_area != id_area) or (id_colaborador and d.id_colaborador != id_colaborador):
                        continue
                    filas.append([f"{liq.mes:02d}/{liq.anio}", d.colaborador.nombre_completo, d.tardanzas, d.faltas, d.abandonos,
                                  "Apto" if d.apto else "No apto", f"{d.monto:.2f}"])
        elif tipo == "sanciones":
            cab = ["Fecha", "Colaborador", "DNI", "Medida", "Estado"]
            filas = [[md.fecha.strftime("%d/%m/%Y"), md.colaborador.nombre_completo, md.colaborador.dni, TIPOS_MEDIDA[md.tipo], md.estado.title()]
                     for md in MedidaRepositorio.recientes(500) if desde <= md.fecha <= hasta
                     and (not id_area or md.colaborador.id_area == id_area) and (not id_colaborador or md.id_colaborador == id_colaborador)]
        else:
            raise ErrorNegocio("Tipo de reporte no válido.")
        return cab, filas

    @classmethod
    def exportar(cls, tipo, formato, desde, hasta, actor, id_area=None, id_colaborador=None, ip=None):
        cab, filas = cls.datos(tipo, desde, hasta, id_area, id_colaborador)
        if not filas:
            raise ErrorNegocio("No hay datos para los filtros seleccionados.")
        titulo = f"{cls.TIPOS[tipo]} del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}"
        buf = io.BytesIO()
        if formato == "excel":
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
            wb = Workbook()
            ws = wb.active
            ws.title = tipo.capitalize()
            ws.append([titulo])
            ws["A1"].font = Font(bold=True, size=13)
            ws.append(cab)
            for celda in ws[2]:
                celda.font, celda.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F2A44")
            for f in filas:
                ws.append(f)
            for col in ws.columns:
                ws.column_dimensions[col[1].column_letter].width = max(12, max(len(str(c.value or "")) for c in col[1:]) + 2)
            wb.save(buf)
            ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
            doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
            t = Table([cab] + filas, repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2A44")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C9D1DD")),
                                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF2F7")])]))
            est = getSampleStyleSheet()
            doc.build([Paragraph("Funeraria Del Castillo", est["Title"]), Paragraph(titulo, est["Heading3"]), Spacer(1, 8), t])
            ext, mime = "pdf", "application/pdf"
        buf.seek(0)
        BitacoraService.registrar(actor.id_usuario, "EXPORTAR", "Reportes", f"{cls.TIPOS[tipo]} ({ext})", ip)
        return buf, f"{tipo}_{desde:%Y%m%d}_{hasta:%Y%m%d}.{ext}", mime


class SincronizacionConsulta:
    @staticmethod
    def historial():
        return SincronizacionRepositorio.recientes()
