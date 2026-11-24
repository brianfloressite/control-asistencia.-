"""CAPA DE DATOS - Modelos ORM (Flask-SQLAlchemy) de la base de datos bd_asistencia.

Implementan el diagrama físico de 22 tablas. Las reglas de inalterabilidad (RNF4) se
respetan desde la capa de negocio: las marcas nunca se eliminan; las correcciones se
registran en `validacion` con usuario, fecha y motivo.
"""
from datetime import datetime
from flask_login import UserMixin
from app.extensions import db

ahora = datetime.now

# Tipos de llave: en MySQL se usan SMALLINT/BIGINT; en SQLite (pruebas) INTEGER para que funcione AUTOINCREMENT
SMALLPK = db.SmallInteger().with_variant(db.Integer, "sqlite")
BIGPK = db.BigInteger().with_variant(db.Integer, "sqlite")


class Perfil(db.Model):
    __tablename__ = "perfil"
    id_perfil = db.Column(SMALLPK, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(30), nullable=False, unique=True)
    descripcion = db.Column(db.String(150))


class Area(db.Model):
    __tablename__ = "area"
    id_area = db.Column(SMALLPK, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    estado = db.Column(db.Boolean, nullable=False, default=True)


class Cargo(db.Model):
    __tablename__ = "cargo"
    id_cargo = db.Column(SMALLPK, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(60), nullable=False, unique=True)
    estado = db.Column(db.Boolean, nullable=False, default=True)


class Colaborador(db.Model):
    __tablename__ = "colaborador"
    id_colaborador = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dni = db.Column(db.String(8), nullable=False, unique=True)
    nombres = db.Column(db.String(60), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)
    id_area = db.Column(db.SmallInteger, db.ForeignKey("area.id_area"), nullable=False)
    id_cargo = db.Column(db.SmallInteger, db.ForeignKey("cargo.id_cargo"), nullable=False)
    id_supervisor = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"))
    codigo_biometrico = db.Column(db.String(20), nullable=False, unique=True)
    fecha_ingreso = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum("ACTIVO", "CESADO", name="estado_colaborador"), nullable=False, default="ACTIVO")
    fecha_cese = db.Column(db.Date)
    motivo_cese = db.Column(db.String(150))

    area = db.relationship("Area")
    cargo = db.relationship("Cargo")
    supervisor = db.relationship("Colaborador", remote_side=[id_colaborador])

    @property
    def nombre_completo(self):
        return f"{self.apellidos}, {self.nombres}"


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"))
    id_perfil = db.Column(db.SmallInteger, db.ForeignKey("perfil.id_perfil"), nullable=False)
    username = db.Column(db.String(40), nullable=False, unique=True)
    password_hash = db.Column(db.String(60), nullable=False)
    estado = db.Column(db.Enum("ACTIVO", "INACTIVO", "BLOQUEADO", name="estado_usuario"), nullable=False, default="ACTIVO")
    intentos_fallidos = db.Column(db.SmallInteger, nullable=False, default=0)
    ultimo_acceso = db.Column(db.DateTime)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora)

    perfil = db.relationship("Perfil")
    colaborador = db.relationship("Colaborador")

    def get_id(self):
        return str(self.id_usuario)

    @property
    def is_active(self):
        return self.estado == "ACTIVO"

    def tiene_perfil(self, *nombres):
        return self.perfil is not None and self.perfil.nombre in nombres


class Horario(db.Model):
    __tablename__ = "horario"
    id_horario = db.Column(SMALLPK, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False)
    hora_entrada = db.Column(db.Time, nullable=False)
    hora_salida = db.Column(db.Time, nullable=False)
    tolerancia_min = db.Column(db.SmallInteger, nullable=False, default=10)
    es_guardia_24h = db.Column(db.Boolean, nullable=False, default=False)


class TurnoAsignado(db.Model):
    __tablename__ = "turno_asignado"
    id_turno = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"), nullable=False, index=True)
    id_horario = db.Column(db.SmallInteger, db.ForeignKey("horario.id_horario"), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)

    colaborador = db.relationship("Colaborador")
    horario = db.relationship("Horario")


class RelojBiometrico(db.Model):
    __tablename__ = "reloj_biometrico"
    id_reloj = db.Column(SMALLPK, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    puerto = db.Column(db.Integer, nullable=False, default=4370)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class SincronizacionLog(db.Model):
    __tablename__ = "sincronizacion_log"
    id_sync = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_reloj = db.Column(db.SmallInteger, db.ForeignKey("reloj_biometrico.id_reloj"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"))
    tipo = db.Column(db.Enum("AUTOMATICA", "MANUAL", name="tipo_sync"), nullable=False)
    inicio = db.Column(db.DateTime, nullable=False, default=ahora)
    fin = db.Column(db.DateTime)
    marcas_descargadas = db.Column(db.Integer, nullable=False, default=0)
    estado = db.Column(db.Enum("EXITOSA", "ERROR", name="estado_sync"), nullable=False)
    mensaje = db.Column(db.String(255))

    reloj = db.relationship("RelojBiometrico")
    usuario = db.relationship("Usuario")


class DispositivoAutorizado(db.Model):
    __tablename__ = "dispositivo_autorizado"
    id_dispositivo = db.Column(SMALLPK, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(60), nullable=False)
    tipo = db.Column(db.Enum("PC", "CELULAR", name="tipo_dispositivo"), nullable=False)
    identificador = db.Column(db.String(100), nullable=False, unique=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class ReporteFalla(db.Model):
    __tablename__ = "reporte_falla"
    id_reporte = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_reloj = db.Column(db.SmallInteger, db.ForeignKey("reloj_biometrico.id_reloj"), nullable=False)
    tipo_falla = db.Column(db.Enum("ENERGIA", "RED", "LECTURA", name="tipo_falla"), nullable=False)
    descripcion = db.Column(db.String(255))
    fecha_hora = db.Column(db.DateTime, nullable=False, default=ahora)
    estado = db.Column(db.Enum("ABIERTO", "CERRADO", name="estado_reporte"), nullable=False, default="ABIERTO")

    reloj = db.relationship("RelojBiometrico")
    colaboradores = db.relationship("ReporteFallaColaborador", back_populates="reporte")


class ReporteFallaColaborador(db.Model):
    __tablename__ = "reporte_falla_colaborador"
    id_reporte = db.Column(db.Integer, db.ForeignKey("reporte_falla.id_reporte"), primary_key=True)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"), primary_key=True)
    fecha_hora = db.Column(db.DateTime, nullable=False, default=ahora)

    reporte = db.relationship("ReporteFalla", back_populates="colaboradores")
    colaborador = db.relationship("Colaborador")


class Marca(db.Model):
    __tablename__ = "marca"
    __table_args__ = (db.UniqueConstraint("id_colaborador", "fecha_hora", "tipo", name="uq_marca"),
                      db.Index("ix_marca_colab_fecha", "id_colaborador", "fecha_hora"))
    id_marca = db.Column(BIGPK, primary_key=True, autoincrement=True)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"), nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False)
    tipo = db.Column(db.Enum("ENTRADA", "SALIDA", name="tipo_marca"), nullable=False)
    origen = db.Column(db.Enum("BIOMETRICO", "CONTINGENCIA", name="origen_marca"), nullable=False)
    id_reloj = db.Column(db.SmallInteger, db.ForeignKey("reloj_biometrico.id_reloj"))
    id_dispositivo = db.Column(db.SmallInteger, db.ForeignKey("dispositivo_autorizado.id_dispositivo"))
    id_reporte = db.Column(db.Integer, db.ForeignKey("reporte_falla.id_reporte"))
    motivo = db.Column(db.String(150))
    ip_origen = db.Column(db.String(45))
    estado = db.Column(db.Enum("PENDIENTE", "APROBADA", "RECHAZADA", name="estado_marca"), nullable=False, default="APROBADA")

    colaborador = db.relationship("Colaborador")
    dispositivo = db.relationship("DispositivoAutorizado")
    reporte = db.relationship("ReporteFalla")


class Inconsistencia(db.Model):
    __tablename__ = "inconsistencia"
    __table_args__ = (db.UniqueConstraint("id_colaborador", "fecha", "tipo", name="uq_inconsistencia"),)
    id_inconsistencia = db.Column(BIGPK, primary_key=True, autoincrement=True)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"), nullable=False)
    id_turno = db.Column(db.Integer, db.ForeignKey("turno_asignado.id_turno"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    tipo = db.Column(db.Enum("TARDANZA", "FALTA", "OMISION", "ABANDONO", name="tipo_inconsistencia"), nullable=False)
    minutos = db.Column(db.Integer, nullable=False, default=0)
    estado = db.Column(db.Enum("DETECTADA", "POR_JUSTIFICAR", "JUSTIFICADA", "CONFIRMADA", name="estado_inconsistencia"),
                       nullable=False, default="DETECTADA")
    observacion = db.Column(db.String(255))

    colaborador = db.relationship("Colaborador")
    turno = db.relationship("TurnoAsignado")


class Justificacion(db.Model):
    __tablename__ = "justificacion"
    id_justificacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_inconsistencia = db.Column(BIGPK,
                                  db.ForeignKey("inconsistencia.id_inconsistencia"), nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    ruta_evidencia = db.Column(db.String(255))
    fecha_registro = db.Column(db.DateTime, nullable=False, default=ahora)
    estado = db.Column(db.Enum("PENDIENTE", "APROBADA", "RECHAZADA", name="estado_justificacion"), nullable=False, default="PENDIENTE")

    inconsistencia = db.relationship("Inconsistencia")


class Validacion(db.Model):
    __tablename__ = "validacion"
    id_validacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=False)
    id_marca = db.Column(BIGPK, db.ForeignKey("marca.id_marca"))
    id_justificacion = db.Column(db.Integer, db.ForeignKey("justificacion.id_justificacion"))
    decision = db.Column(db.Enum("APROBADA", "RECHAZADA", name="decision_validacion"), nullable=False)
    observacion = db.Column(db.String(255))
    fecha_hora = db.Column(db.DateTime, nullable=False, default=ahora)

    usuario = db.relationship("Usuario")


class ReglaNegocio(db.Model):
    __tablename__ = "regla_negocio"
    id_regla = db.Column(SMALLPK, primary_key=True, autoincrement=True)
    tolerancia_min = db.Column(db.SmallInteger, nullable=False)
    monto_bono = db.Column(db.Numeric(8, 2), nullable=False)
    max_tardanzas_bono = db.Column(db.SmallInteger, nullable=False)
    tardanzas_alerta = db.Column(db.SmallInteger, nullable=False)
    faltas_alerta = db.Column(db.SmallInteger, nullable=False)
    vigencia_desde = db.Column(db.Date, nullable=False)
    vigente = db.Column(db.Boolean, nullable=False, default=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=False)

    usuario = db.relationship("Usuario")


class LiquidacionBono(db.Model):
    __tablename__ = "liquidacion_bono"
    __table_args__ = (db.UniqueConstraint("anio", "mes", name="uq_liquidacion_periodo"),)
    id_liquidacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    anio = db.Column(db.SmallInteger, nullable=False)
    mes = db.Column(db.SmallInteger, nullable=False)
    id_regla = db.Column(db.SmallInteger, db.ForeignKey("regla_negocio.id_regla"), nullable=False)
    estado = db.Column(db.Enum("BORRADOR", "CERRADA", name="estado_liquidacion"), nullable=False, default="BORRADOR")
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=False)
    fecha_cierre = db.Column(db.DateTime)

    regla = db.relationship("ReglaNegocio")
    detalles = db.relationship("BonoDetalle", back_populates="liquidacion", cascade="all, delete-orphan")


class BonoDetalle(db.Model):
    __tablename__ = "bono_detalle"
    id_detalle = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_liquidacion = db.Column(db.Integer, db.ForeignKey("liquidacion_bono.id_liquidacion"), nullable=False)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"), nullable=False)
    tardanzas = db.Column(db.SmallInteger, nullable=False, default=0)
    faltas = db.Column(db.SmallInteger, nullable=False, default=0)
    abandonos = db.Column(db.SmallInteger, nullable=False, default=0)
    apto = db.Column(db.Boolean, nullable=False)
    monto = db.Column(db.Numeric(8, 2), nullable=False, default=0)

    liquidacion = db.relationship("LiquidacionBono", back_populates="detalles")
    colaborador = db.relationship("Colaborador")


class AlertaDisciplinaria(db.Model):
    __tablename__ = "alerta_disciplinaria"
    id_alerta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"), nullable=False)
    id_regla = db.Column(db.SmallInteger, db.ForeignKey("regla_negocio.id_regla"), nullable=False)
    tipo = db.Column(db.Enum("TARDANZAS", "FALTAS", name="tipo_alerta"), nullable=False)
    cantidad = db.Column(db.SmallInteger, nullable=False)
    fecha_generacion = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum("ACTIVA", "ATENDIDA", "DESCARTADA", name="estado_alerta"), nullable=False, default="ACTIVA")
    motivo_descarte = db.Column(db.String(255))

    colaborador = db.relationship("Colaborador")


class MedidaDisciplinaria(db.Model):
    __tablename__ = "medida_disciplinaria"
    id_medida = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_alerta = db.Column(db.Integer, db.ForeignKey("alerta_disciplinaria.id_alerta"), nullable=False)
    id_colaborador = db.Column(db.Integer, db.ForeignKey("colaborador.id_colaborador"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=False)
    tipo = db.Column(db.Enum("AMONESTACION_VERBAL", "AMONESTACION_ESCRITA", "SUSPENSION", "CESE", name="tipo_medida"), nullable=False)
    sustento = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    ruta_carta_pdf = db.Column(db.String(255))
    estado = db.Column(db.Enum("REGISTRADA", "NOTIFICADA", "CERRADA", name="estado_medida"), nullable=False, default="REGISTRADA")

    alerta = db.relationship("AlertaDisciplinaria")
    colaborador = db.relationship("Colaborador")


class Bitacora(db.Model):
    __tablename__ = "bitacora"
    id_bitacora = db.Column(BIGPK, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"))
    fecha_hora = db.Column(db.DateTime, nullable=False, default=ahora, index=True)
    accion = db.Column(db.String(30), nullable=False)
    modulo = db.Column(db.String(40), nullable=False)
    detalle = db.Column(db.String(255))
    ip = db.Column(db.String(45))

    usuario = db.relationship("Usuario")
