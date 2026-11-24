"""CAPA DE DATOS - Repositorios (patrón Repository).

Encapsulan las consultas a la base de datos para que la capa de negocio no dependa
de SQLAlchemy directamente. Cada repositorio expone operaciones de lectura y escritura
de una entidad o agregado.
"""
from datetime import datetime, date, time, timedelta
from sqlalchemy import func, and_, or_
from app.extensions import db
from app.datos import modelos as m


class RepositorioBase:
    modelo = None

    @classmethod
    def obtener(cls, id_):
        return db.session.get(cls.modelo, id_)

    @classmethod
    def listar(cls, **filtros):
        return cls.modelo.query.filter_by(**filtros).all()

    @staticmethod
    def agregar(obj):
        db.session.add(obj)
        return obj

    @staticmethod
    def guardar():
        db.session.commit()

    @staticmethod
    def deshacer():
        db.session.rollback()


class PerfilRepositorio(RepositorioBase):
    modelo = m.Perfil

    @staticmethod
    def por_nombre(nombre):
        return m.Perfil.query.filter_by(nombre=nombre).first()


class UsuarioRepositorio(RepositorioBase):
    modelo = m.Usuario

    @staticmethod
    def por_username(username):
        return m.Usuario.query.filter(func.lower(m.Usuario.username) == username.lower()).first()

    @staticmethod
    def todos():
        return m.Usuario.query.order_by(m.Usuario.username).all()


class AreaRepositorio(RepositorioBase):
    modelo = m.Area


class CargoRepositorio(RepositorioBase):
    modelo = m.Cargo


class ColaboradorRepositorio(RepositorioBase):
    modelo = m.Colaborador

    @staticmethod
    def buscar(texto=None, id_area=None, id_cargo=None, estado=None):
        q = m.Colaborador.query
        if texto:
            like = f"%{texto}%"
            q = q.filter(or_(m.Colaborador.dni.like(like), m.Colaborador.nombres.like(like), m.Colaborador.apellidos.like(like)))
        if id_area:
            q = q.filter_by(id_area=id_area)
        if id_cargo:
            q = q.filter_by(id_cargo=id_cargo)
        if estado:
            q = q.filter_by(estado=estado)
        return q.order_by(m.Colaborador.apellidos)

    @staticmethod
    def por_dni(dni):
        return m.Colaborador.query.filter_by(dni=dni).first()

    @staticmethod
    def por_codigo(codigo):
        return m.Colaborador.query.filter_by(codigo_biometrico=str(codigo)).first()

    @staticmethod
    def activos(id_area=None):
        q = m.Colaborador.query.filter_by(estado="ACTIVO")
        if id_area:
            q = q.filter_by(id_area=id_area)
        return q.order_by(m.Colaborador.apellidos).all()


class HorarioRepositorio(RepositorioBase):
    modelo = m.Horario


class TurnoRepositorio(RepositorioBase):
    modelo = m.TurnoAsignado

    @staticmethod
    def cruces(id_colaborador, desde, hasta, excluir=None):
        q = m.TurnoAsignado.query.filter(m.TurnoAsignado.id_colaborador == id_colaborador,
                                         m.TurnoAsignado.fecha_inicio <= hasta, m.TurnoAsignado.fecha_fin >= desde)
        if excluir:
            q = q.filter(m.TurnoAsignado.id_turno != excluir)
        return q.all()

    @staticmethod
    def vigente(id_colaborador, fecha):
        return m.TurnoAsignado.query.filter(m.TurnoAsignado.id_colaborador == id_colaborador,
                                            m.TurnoAsignado.fecha_inicio <= fecha, m.TurnoAsignado.fecha_fin >= fecha).first()

    @staticmethod
    def en_rango(desde, hasta, id_area=None):
        q = m.TurnoAsignado.query.join(m.Colaborador).filter(
            m.TurnoAsignado.fecha_inicio <= hasta, m.TurnoAsignado.fecha_fin >= desde, m.Colaborador.estado == "ACTIVO")
        if id_area:
            q = q.filter(m.Colaborador.id_area == id_area)
        return q.all()

    @staticmethod
    def recientes(limite=50):
        return m.TurnoAsignado.query.order_by(m.TurnoAsignado.fecha_inicio.desc()).limit(limite).all()


class RelojRepositorio(RepositorioBase):
    modelo = m.RelojBiometrico

    @staticmethod
    def activos():
        return m.RelojBiometrico.query.filter_by(activo=True).all()


class SincronizacionRepositorio(RepositorioBase):
    modelo = m.SincronizacionLog

    @staticmethod
    def recientes(limite=20):
        return m.SincronizacionLog.query.order_by(m.SincronizacionLog.inicio.desc()).limit(limite).all()


class DispositivoRepositorio(RepositorioBase):
    modelo = m.DispositivoAutorizado

    @staticmethod
    def autorizado(identificador):
        if not identificador:
            return None
        return m.DispositivoAutorizado.query.filter_by(identificador=identificador, activo=True).first()


class ReporteFallaRepositorio(RepositorioBase):
    modelo = m.ReporteFalla

    @staticmethod
    def abierto_reciente(tipo, horas=1):
        limite = datetime.now() - timedelta(hours=horas)
        return m.ReporteFalla.query.filter(m.ReporteFalla.tipo_falla == tipo, m.ReporteFalla.estado == "ABIERTO",
                                           m.ReporteFalla.fecha_hora >= limite).order_by(m.ReporteFalla.fecha_hora.desc()).first()

    @staticmethod
    def abierto_cualquiera(horas=1):
        limite = datetime.now() - timedelta(hours=horas)
        return m.ReporteFalla.query.filter(m.ReporteFalla.estado == "ABIERTO", m.ReporteFalla.fecha_hora >= limite)\
            .order_by(m.ReporteFalla.fecha_hora.desc()).first()

    @staticmethod
    def recientes(limite=20):
        return m.ReporteFalla.query.order_by(m.ReporteFalla.fecha_hora.desc()).limit(limite).all()


class MarcaRepositorio(RepositorioBase):
    modelo = m.Marca

    @staticmethod
    def existe(id_colaborador, fecha_hora, tipo):
        return m.Marca.query.filter_by(id_colaborador=id_colaborador, fecha_hora=fecha_hora, tipo=tipo).first() is not None

    @staticmethod
    def ultima_del_colaborador(id_colaborador, tipo, desde):
        return m.Marca.query.filter(m.Marca.id_colaborador == id_colaborador, m.Marca.tipo == tipo,
                                    m.Marca.fecha_hora >= desde, m.Marca.estado != "RECHAZADA").first()

    @staticmethod
    def del_colaborador(id_colaborador, desde, hasta):
        return m.Marca.query.filter(m.Marca.id_colaborador == id_colaborador,
                                    m.Marca.fecha_hora >= datetime.combine(desde, time.min),
                                    m.Marca.fecha_hora <= datetime.combine(hasta, time.max)).order_by(m.Marca.fecha_hora).all()

    @staticmethod
    def pendientes_contingencia(id_colaborador=None, desde=None, hasta=None):
        q = m.Marca.query.filter_by(origen="CONTINGENCIA", estado="PENDIENTE")
        if id_colaborador:
            q = q.filter_by(id_colaborador=id_colaborador)
        if desde:
            q = q.filter(m.Marca.fecha_hora >= datetime.combine(desde, time.min))
        if hasta:
            q = q.filter(m.Marca.fecha_hora <= datetime.combine(hasta, time.max))
        return q.order_by(m.Marca.fecha_hora.desc()).all()

    @staticmethod
    def contar_pendientes_periodo(desde, hasta):
        return m.Marca.query.filter(m.Marca.estado == "PENDIENTE", m.Marca.fecha_hora >= datetime.combine(desde, time.min),
                                    m.Marca.fecha_hora <= datetime.combine(hasta, time.max)).count()

    @staticmethod
    def contar_dia(fecha):
        return m.Marca.query.filter(m.Marca.fecha_hora >= datetime.combine(fecha, time.min),
                                    m.Marca.fecha_hora <= datetime.combine(fecha, time.max)).count()


class InconsistenciaRepositorio(RepositorioBase):
    modelo = m.Inconsistencia

    @staticmethod
    def buscar(desde, hasta, id_area=None, tipo=None, id_colaborador=None):
        q = m.Inconsistencia.query.join(m.Colaborador).filter(m.Inconsistencia.fecha >= desde, m.Inconsistencia.fecha <= hasta)
        if id_area:
            q = q.filter(m.Colaborador.id_area == id_area)
        if tipo:
            q = q.filter(m.Inconsistencia.tipo == tipo)
        if id_colaborador:
            q = q.filter(m.Inconsistencia.id_colaborador == id_colaborador)
        return q.order_by(m.Inconsistencia.fecha.desc()).all()

    @staticmethod
    def existente(id_colaborador, fecha, tipo):
        return m.Inconsistencia.query.filter_by(id_colaborador=id_colaborador, fecha=fecha, tipo=tipo).first()

    @staticmethod
    def conteo_por_tipo(id_colaborador, desde, hasta):
        filas = db.session.query(m.Inconsistencia.tipo, func.count()).filter(
            m.Inconsistencia.id_colaborador == id_colaborador, m.Inconsistencia.fecha >= desde, m.Inconsistencia.fecha <= hasta,
            m.Inconsistencia.estado != "JUSTIFICADA").group_by(m.Inconsistencia.tipo).all()
        return {t: c for t, c in filas}


class JustificacionRepositorio(RepositorioBase):
    modelo = m.Justificacion

    @staticmethod
    def pendientes():
        return m.Justificacion.query.filter_by(estado="PENDIENTE").order_by(m.Justificacion.fecha_registro.desc()).all()


class ValidacionRepositorio(RepositorioBase):
    modelo = m.Validacion


class ReglaRepositorio(RepositorioBase):
    modelo = m.ReglaNegocio

    @staticmethod
    def vigente(fecha=None):
        fecha = fecha or date.today()
        regla = m.ReglaNegocio.query.filter(m.ReglaNegocio.vigencia_desde <= fecha)\
            .order_by(m.ReglaNegocio.vigencia_desde.desc(), m.ReglaNegocio.id_regla.desc()).first()
        return regla or m.ReglaNegocio.query.filter_by(vigente=True).first()

    @staticmethod
    def historial():
        return m.ReglaNegocio.query.order_by(m.ReglaNegocio.vigencia_desde.desc(), m.ReglaNegocio.id_regla.desc()).all()


class LiquidacionRepositorio(RepositorioBase):
    modelo = m.LiquidacionBono

    @staticmethod
    def por_periodo(anio, mes):
        return m.LiquidacionBono.query.filter_by(anio=anio, mes=mes).first()

    @staticmethod
    def bonos_del_colaborador(id_colaborador):
        return m.BonoDetalle.query.join(m.LiquidacionBono).filter(m.BonoDetalle.id_colaborador == id_colaborador)\
            .order_by(m.LiquidacionBono.anio.desc(), m.LiquidacionBono.mes.desc()).all()


class AlertaRepositorio(RepositorioBase):
    modelo = m.AlertaDisciplinaria

    @staticmethod
    def activas():
        return m.AlertaDisciplinaria.query.filter_by(estado="ACTIVA").order_by(m.AlertaDisciplinaria.fecha_generacion.desc()).all()

    @staticmethod
    def activa_de(id_colaborador, tipo):
        return m.AlertaDisciplinaria.query.filter_by(id_colaborador=id_colaborador, tipo=tipo, estado="ACTIVA").first()


class MedidaRepositorio(RepositorioBase):
    modelo = m.MedidaDisciplinaria

    @staticmethod
    def recientes(limite=30):
        return m.MedidaDisciplinaria.query.order_by(m.MedidaDisciplinaria.fecha.desc()).limit(limite).all()

    @staticmethod
    def activas_count():
        return m.MedidaDisciplinaria.query.filter(m.MedidaDisciplinaria.estado != "CERRADA").count()


class BitacoraRepositorio(RepositorioBase):
    modelo = m.Bitacora

    @staticmethod
    def buscar(id_usuario=None, accion=None, desde=None, hasta=None):
        q = m.Bitacora.query
        if id_usuario:
            q = q.filter(m.Bitacora.id_usuario == id_usuario)
        if accion:
            q = q.filter(m.Bitacora.accion == accion)
        if desde:
            q = q.filter(m.Bitacora.fecha_hora >= datetime.combine(desde, time.min))
        if hasta:
            q = q.filter(m.Bitacora.fecha_hora <= datetime.combine(hasta, time.max))
        return q.order_by(m.Bitacora.fecha_hora.desc())

    @staticmethod
    def acciones():
        return [a for (a,) in db.session.query(m.Bitacora.accion).distinct().order_by(m.Bitacora.accion).all()]
