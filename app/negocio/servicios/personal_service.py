"""Módulo de Gestión de Personal y Turnos: colaboradores (CU03) y horarios/turnos (CU04)."""
import re
from datetime import date, datetime
from app.datos import modelos as m
from app.datos.repositorios import (ColaboradorRepositorio, AreaRepositorio, CargoRepositorio,
                                    HorarioRepositorio, TurnoRepositorio)
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.seguridad_service import BitacoraService


def _fecha(valor, campo):
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ErrorNegocio(f"Ingrese una fecha válida en «{campo}».")


def _hora(valor, campo):
    try:
        return datetime.strptime(valor, "%H:%M").time()
    except (TypeError, ValueError):
        raise ErrorNegocio(f"Ingrese una hora válida en «{campo}».")


class ColaboradorService:
    @staticmethod
    def buscar(**filtros):
        return ColaboradorRepositorio.buscar(**filtros)

    @staticmethod
    def catalogos():
        return AreaRepositorio.listar(estado=True), CargoRepositorio.listar(estado=True)

    @staticmethod
    def guardar(datos, actor, ip=None, id_colaborador=None):
        dni = (datos.get("dni") or "").strip()
        if not re.fullmatch(r"\d{8}", dni):
            raise ErrorNegocio("El DNI debe tener 8 dígitos.")
        codigo = (datos.get("codigo_biometrico") or "").strip()
        if not codigo:
            raise ErrorNegocio("Ingrese el código biométrico.")
        nombres, apellidos = (datos.get("nombres") or "").strip(), (datos.get("apellidos") or "").strip()
        if not nombres or not apellidos:
            raise ErrorNegocio("Ingrese nombres y apellidos.")
        otro = ColaboradorRepositorio.por_dni(dni)
        if otro and otro.id_colaborador != id_colaborador:
            raise ErrorNegocio("Ya existe un colaborador con ese DNI.")
        otro = ColaboradorRepositorio.por_codigo(codigo)
        if otro and otro.id_colaborador != id_colaborador:
            raise ErrorNegocio("El código biométrico ya está asignado a otro colaborador.")
        if AreaRepositorio.obtener(int(datos.get("id_area") or 0)) is None or CargoRepositorio.obtener(int(datos.get("id_cargo") or 0)) is None:
            raise ErrorNegocio("Seleccione el área y el cargo.")
        if id_colaborador:
            c = ColaboradorRepositorio.obtener(id_colaborador)
            accion = "ACTUALIZAR"
        else:
            c = m.Colaborador(estado="ACTIVO")
            ColaboradorRepositorio.agregar(c)
            accion = "CREAR"
        c.dni, c.nombres, c.apellidos, c.codigo_biometrico = dni, nombres, apellidos, codigo
        c.id_area, c.id_cargo = int(datos["id_area"]), int(datos["id_cargo"])
        c.id_supervisor = int(datos["id_supervisor"]) if datos.get("id_supervisor") else None
        c.fecha_ingreso = _fecha(datos.get("fecha_ingreso"), "Fecha de ingreso")
        BitacoraService.registrar(actor.id_usuario, accion, "Personal", f"Colaborador {dni} {apellidos}", ip, commit=False)
        ColaboradorRepositorio.guardar()
        return c

    @staticmethod
    def dar_baja(id_colaborador, fecha_cese, motivo, actor, ip=None):
        c = ColaboradorRepositorio.obtener(id_colaborador)
        if c is None:
            raise ErrorNegocio("Colaborador no encontrado.")
        if not motivo:
            raise ErrorNegocio("Indique el motivo del cese.")
        c.estado, c.fecha_cese, c.motivo_cese = "CESADO", _fecha(fecha_cese, "Fecha de cese"), motivo
        BitacoraService.registrar(actor.id_usuario, "BAJA", "Personal", f"Cese de {c.dni}: {motivo}", ip, commit=False)
        ColaboradorRepositorio.guardar()


class TurnoService:
    @staticmethod
    def horarios():
        return HorarioRepositorio.listar()

    @staticmethod
    def crear_horario(datos, actor, ip=None):
        nombre = (datos.get("nombre") or "").strip()
        if not nombre:
            raise ErrorNegocio("Ingrese el nombre del horario.")
        tol = int(datos.get("tolerancia_min") or 0)
        if tol < 0 or tol > 60:
            raise ErrorNegocio("La tolerancia debe estar entre 0 y 60 minutos.")
        h = m.Horario(nombre=nombre, hora_entrada=_hora(datos.get("hora_entrada"), "Entrada"),
                      hora_salida=_hora(datos.get("hora_salida"), "Salida"), tolerancia_min=tol,
                      es_guardia_24h=bool(datos.get("es_guardia_24h")))
        HorarioRepositorio.agregar(h)
        BitacoraService.registrar(actor.id_usuario, "CREAR", "Turnos", f"Horario {nombre}", ip, commit=False)
        HorarioRepositorio.guardar()
        return h

    @staticmethod
    def asignar(datos, actor, ip=None):
        colab = ColaboradorRepositorio.obtener(int(datos.get("id_colaborador") or 0))
        horario = HorarioRepositorio.obtener(int(datos.get("id_horario") or 0))
        if colab is None or horario is None:
            raise ErrorNegocio("Seleccione colaborador y horario.")
        if colab.estado != "ACTIVO":
            raise ErrorNegocio("Solo se pueden asignar turnos a colaboradores activos.")
        desde, hasta = _fecha(datos.get("fecha_inicio"), "Desde"), _fecha(datos.get("fecha_fin"), "Hasta")
        if desde > hasta:
            raise ErrorNegocio("La fecha de inicio no puede ser posterior a la fecha de fin.")
        cruces = TurnoRepositorio.cruces(colab.id_colaborador, desde, hasta)
        if cruces:
            c = cruces[0]
            raise ErrorNegocio(f"Cruce de turnos: {colab.nombre_completo} ya tiene «{c.horario.nombre}» del "
                               f"{c.fecha_inicio:%d/%m/%Y} al {c.fecha_fin:%d/%m/%Y}.")
        t = m.TurnoAsignado(id_colaborador=colab.id_colaborador, id_horario=horario.id_horario, fecha_inicio=desde, fecha_fin=hasta)
        TurnoRepositorio.agregar(t)
        BitacoraService.registrar(actor.id_usuario, "ASIGNAR", "Turnos", f"{colab.dni} → {horario.nombre} {desde}..{hasta}", ip, commit=False)
        TurnoRepositorio.guardar()
        return t

    @staticmethod
    def asignaciones():
        return TurnoRepositorio.recientes()
