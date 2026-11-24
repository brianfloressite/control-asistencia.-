"""Módulo de Auditoría de Asistencia: validaciones (CU08) e inconsistencias (CU09)."""
from datetime import datetime, date, timedelta
from app.datos import modelos as m
from app.datos.repositorios import (MarcaRepositorio, JustificacionRepositorio, ValidacionRepositorio, TurnoRepositorio,
                                    InconsistenciaRepositorio, ReglaRepositorio)
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.seguridad_service import BitacoraService


class ValidacionService:
    @staticmethod
    def pendientes(id_colaborador=None, desde=None, hasta=None):
        return MarcaRepositorio.pendientes_contingencia(id_colaborador, desde, hasta), JustificacionRepositorio.pendientes()

    @staticmethod
    def resolver_marcas(ids, decision, observacion, actor, ip=None):
        if decision not in ("APROBADA", "RECHAZADA"):
            raise ErrorNegocio("Decisión inválida.")
        if decision == "RECHAZADA" and not (observacion or "").strip():
            raise ErrorNegocio("Indique el motivo del rechazo.")
        if not ids:
            raise ErrorNegocio("Seleccione al menos una marca.")
        n = 0
        for id_ in ids:
            marca = MarcaRepositorio.obtener(int(id_))
            if marca is None or marca.estado != "PENDIENTE":
                continue
            marca.estado = decision  # la marca no se edita: solo cambia su estado y queda la validación como ajuste
            ValidacionRepositorio.agregar(m.Validacion(id_usuario=actor.id_usuario, id_marca=marca.id_marca,
                                                       decision=decision, observacion=(observacion or "")[:255]))
            n += 1
        BitacoraService.registrar(actor.id_usuario, "VALIDAR", "Auditoría", f"{n} marca(s) {decision.lower()}", ip, commit=False)
        ValidacionRepositorio.guardar()
        return n

    @staticmethod
    def resolver_justificacion(id_justificacion, decision, observacion, actor, ip=None):
        j = JustificacionRepositorio.obtener(id_justificacion)
        if j is None or j.estado != "PENDIENTE":
            raise ErrorNegocio("La justificación no está pendiente.")
        if decision == "RECHAZADA" and not (observacion or "").strip():
            raise ErrorNegocio("Indique el motivo del rechazo.")
        j.estado = decision
        j.inconsistencia.estado = "JUSTIFICADA" if decision == "APROBADA" else "CONFIRMADA"
        ValidacionRepositorio.agregar(m.Validacion(id_usuario=actor.id_usuario, id_justificacion=j.id_justificacion,
                                                   decision=decision, observacion=(observacion or "")[:255]))
        BitacoraService.registrar(actor.id_usuario, "VALIDAR", "Auditoría", f"Justificación #{j.id_justificacion} {decision.lower()}", ip, commit=False)
        ValidacionRepositorio.guardar()

    @staticmethod
    def presentar_justificacion(id_inconsistencia, colaborador, motivo, actor, ip=None):
        inc = InconsistenciaRepositorio.obtener(id_inconsistencia)
        if inc is None or colaborador is None or inc.id_colaborador != colaborador.id_colaborador:
            raise ErrorNegocio("Inconsistencia no encontrada.")
        if not (motivo or "").strip():
            raise ErrorNegocio("Escriba el motivo de la justificación.")
        JustificacionRepositorio.agregar(m.Justificacion(id_inconsistencia=inc.id_inconsistencia, motivo=motivo.strip()[:255]))
        inc.estado = "POR_JUSTIFICAR"
        BitacoraService.registrar(actor.id_usuario, "JUSTIFICAR", "Auditoría", f"Inconsistencia #{inc.id_inconsistencia}", ip, commit=False)
        JustificacionRepositorio.guardar()


class AsistenciaService:
    """Cruza turnos asignados con marcas aprobadas y aplica las tolerancias de la regla vigente."""

    @staticmethod
    def _ventana(turno, dia):
        h = turno.horario
        entrada = datetime.combine(dia, h.hora_entrada)
        salida = datetime.combine(dia, h.hora_salida)
        if h.es_guardia_24h or salida <= entrada:
            salida += timedelta(days=1)
        return entrada, salida

    @classmethod
    def evaluar_dia(cls, turno, dia, marcas, tolerancia, ahora=None):
        """Devuelve una lista [(tipo, minutos)] con las inconsistencias del día (función pura, se prueba sola)."""
        ahora = ahora or datetime.now()
        entrada_esp, salida_esp = cls._ventana(turno, dia)
        desde, hasta = entrada_esp - timedelta(hours=3), salida_esp + timedelta(hours=3)
        validas = [mk for mk in marcas if mk.estado == "APROBADA" and desde <= mk.fecha_hora <= hasta]
        entradas = sorted(mk.fecha_hora for mk in validas if mk.tipo == "ENTRADA")
        salidas = sorted(mk.fecha_hora for mk in validas if mk.tipo == "SALIDA")
        res = []
        if not entradas and not salidas:
            if any(mk.estado == "PENDIENTE" and desde <= mk.fecha_hora <= hasta for mk in marcas):
                return res  # hay una marca de contingencia en validación: aún no se califica el día
            if ahora > entrada_esp + timedelta(minutes=tolerancia):
                res.append(("FALTA", 0))
            return res
        if entradas:
            tarde = int((entradas[0] - entrada_esp).total_seconds() // 60)
            if tarde > tolerancia:
                res.append(("TARDANZA", tarde))
        if salidas:
            antes = int((salida_esp - salidas[-1]).total_seconds() // 60)
            if antes > tolerancia:
                res.append(("ABANDONO", antes))
        if (not entradas or not salidas) and ahora > salida_esp + timedelta(hours=3):
            res.append(("OMISION", 0))
        return res

    @classmethod
    def detectar(cls, desde, hasta, id_area=None, ahora=None):
        if desde > hasta:
            raise ErrorNegocio("La fecha de inicio no puede ser posterior a la fecha de fin.")
        ahora = ahora or datetime.now()
        regla = ReglaRepositorio.vigente(hasta)
        for turno in TurnoRepositorio.en_rango(desde, hasta, id_area):
            tolerancia = regla.tolerancia_min if regla else turno.horario.tolerancia_min
            ini, fin = max(desde, turno.fecha_inicio), min(hasta, turno.fecha_fin, ahora.date())
            if ini > fin:
                continue
            marcas = MarcaRepositorio.del_colaborador(turno.id_colaborador, ini - timedelta(days=1), fin + timedelta(days=1))
            dia = ini
            while dia <= fin:
                for tipo, minutos in cls.evaluar_dia(turno, dia, marcas, tolerancia, ahora):
                    inc = InconsistenciaRepositorio.existente(turno.id_colaborador, dia, tipo)
                    if inc is None:
                        InconsistenciaRepositorio.agregar(m.Inconsistencia(id_colaborador=turno.id_colaborador, id_turno=turno.id_turno,
                                                                           fecha=dia, tipo=tipo, minutos=minutos))
                    elif inc.estado == "DETECTADA":
                        inc.minutos = minutos
                dia += timedelta(days=1)
        InconsistenciaRepositorio.guardar()
        return True

    @classmethod
    def auditar(cls, desde, hasta, id_area=None, tipo=None):
        cls.detectar(desde, hasta, id_area)
        return InconsistenciaRepositorio.buscar(desde, hasta, id_area, tipo)

    @staticmethod
    def observar(id_inconsistencia, texto, solicitar_justificacion, actor, ip=None):
        inc = InconsistenciaRepositorio.obtener(id_inconsistencia)
        if inc is None:
            raise ErrorNegocio("Inconsistencia no encontrada.")
        inc.observacion = (texto or "")[:255] or inc.observacion
        inc.estado = "POR_JUSTIFICAR" if solicitar_justificacion else "CONFIRMADA"
        BitacoraService.registrar(actor.id_usuario, "AUDITAR", "Auditoría", f"Inconsistencia #{inc.id_inconsistencia} → {inc.estado}", ip, commit=False)
        InconsistenciaRepositorio.guardar()
