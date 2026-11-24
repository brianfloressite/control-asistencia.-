"""Pruebas unitarias de la capa de negocio (servicios) y de la capa de datos (repositorios)."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
import pytest
from app.datos import modelos as m
from app.datos.repositorios import UsuarioRepositorio, ColaboradorRepositorio, ReglaRepositorio, MarcaRepositorio
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.seguridad_service import AuthService, UsuarioService
from app.negocio.servicios.personal_service import ColaboradorService, TurnoService
from app.negocio.servicios.marcacion_service import ContingenciaService, BiometricoService
from app.negocio.servicios.auditoria_service import AsistenciaService, ValidacionService
from app.negocio.servicios.incentivos_service import ReglaService, BonoService


def _turno(entrada=time(8), salida=time(16), guardia=False):
    return SimpleNamespace(horario=SimpleNamespace(hora_entrada=entrada, hora_salida=salida, es_guardia_24h=guardia))


def _marca(dt, tipo, estado="APROBADA"):
    return SimpleNamespace(fecha_hora=dt, tipo=tipo, estado=estado)


# ---------- CU01 · Autenticación ----------
def test_login_correcto_reinicia_intentos(ctx):
    u = AuthService.autenticar("rrhh", "Asistencia2026")
    assert u.username == "rrhh" and u.intentos_fallidos == 0 and u.ultimo_acceso is not None


def test_login_bloquea_tras_cinco_intentos(ctx):
    for _ in range(5):
        with pytest.raises(ErrorNegocio):
            AuthService.autenticar("rrhh", "incorrecta")
    assert UsuarioRepositorio.por_username("rrhh").estado == "BLOQUEADO"
    with pytest.raises(ErrorNegocio, match="bloqueado"):
        AuthService.autenticar("rrhh", "Asistencia2026")


def test_contrasena_guardada_con_bcrypt(ctx):
    assert UsuarioRepositorio.por_username("admin").password_hash.startswith("$2b$")


# ---------- CU02 · Usuarios ----------
def test_no_permite_usuario_duplicado(ctx):
    admin = UsuarioRepositorio.por_username("admin")
    perfil = UsuarioService.perfiles()[0]
    with pytest.raises(ErrorNegocio, match="ya existe"):
        UsuarioService.guardar({"username": "rrhh", "password": "ClaveSegura1", "id_perfil": perfil.id_perfil}, admin)


# ---------- CU03 · Colaboradores ----------
def test_dni_debe_tener_ocho_digitos(ctx):
    admin = UsuarioRepositorio.por_username("admin")
    with pytest.raises(ErrorNegocio, match="8 dígitos"):
        ColaboradorService.guardar({"dni": "123", "nombres": "A", "apellidos": "B", "codigo_biometrico": "999",
                                    "id_area": 1, "id_cargo": 1, "fecha_ingreso": "2026-01-01"}, admin)


def test_codigo_biometrico_unico(ctx):
    admin = UsuarioRepositorio.por_username("admin")
    with pytest.raises(ErrorNegocio, match="código biométrico"):
        ColaboradorService.guardar({"dni": "70000001", "nombres": "Ana", "apellidos": "Ruiz", "codigo_biometrico": "101",
                                    "id_area": 1, "id_cargo": 1, "fecha_ingreso": "2026-01-01"}, admin)


# ---------- CU04 · Turnos ----------
def test_detecta_cruce_de_turnos(ctx):
    admin = UsuarioRepositorio.por_username("admin")
    with pytest.raises(ErrorNegocio, match="Cruce de turnos"):
        TurnoService.asignar({"id_colaborador": 4, "id_horario": 1, "fecha_inicio": date.today().isoformat(),
                              "fecha_fin": date.today().isoformat()}, admin)


# ---------- CU09 · Reglas de asistencia (funciones puras) ----------
def test_tardanza_supera_tolerancia():
    dia = date(2026, 11, 10)
    marcas = [_marca(datetime(2026, 11, 10, 8, 25), "ENTRADA"), _marca(datetime(2026, 11, 10, 16, 5), "SALIDA")]
    assert AsistenciaService.evaluar_dia(_turno(), dia, marcas, 10, datetime(2026, 11, 11)) == [("TARDANZA", 25)]


def test_dentro_de_tolerancia_no_es_tardanza():
    dia = date(2026, 11, 10)
    marcas = [_marca(datetime(2026, 11, 10, 8, 9), "ENTRADA"), _marca(datetime(2026, 11, 10, 16, 0), "SALIDA")]
    assert AsistenciaService.evaluar_dia(_turno(), dia, marcas, 10, datetime(2026, 11, 11)) == []


def test_sin_marcas_es_falta_y_omision_si_falta_salida():
    dia = date(2026, 11, 10)
    assert AsistenciaService.evaluar_dia(_turno(), dia, [], 10, datetime(2026, 11, 11)) == [("FALTA", 0)]
    solo_entrada = [_marca(datetime(2026, 11, 10, 8, 0), "ENTRADA")]
    assert AsistenciaService.evaluar_dia(_turno(), dia, solo_entrada, 10, datetime(2026, 11, 11)) == [("OMISION", 0)]


def test_abandono_de_guardia_24h():
    dia = date(2026, 11, 10)
    marcas = [_marca(datetime(2026, 11, 10, 8, 0), "ENTRADA"), _marca(datetime(2026, 11, 11, 2, 0), "SALIDA")]
    assert AsistenciaService.evaluar_dia(_turno(time(8), time(8), True), dia, marcas, 10, datetime(2026, 11, 12)) == [("ABANDONO", 360)]


def test_marca_pendiente_no_se_califica_y_rechazada_es_falta():
    dia = date(2026, 11, 10)
    marcas = [_marca(datetime(2026, 11, 10, 8, 0), "ENTRADA", "PENDIENTE"), _marca(datetime(2026, 11, 10, 16, 0), "SALIDA", "PENDIENTE")]
    assert AsistenciaService.evaluar_dia(_turno(), dia, marcas, 10, datetime(2026, 11, 11)) == []
    rechazadas = [_marca(datetime(2026, 11, 10, 8, 0), "ENTRADA", "RECHAZADA")]
    assert AsistenciaService.evaluar_dia(_turno(), dia, rechazadas, 10, datetime(2026, 11, 11)) == [("FALTA", 0)]


# ---------- CU10 · Reglas de negocio ----------
def test_regla_rechaza_valores_invalidos(ctx):
    rrhh = UsuarioRepositorio.por_username("rrhh")
    with pytest.raises(ErrorNegocio, match="mayores a 0"):
        ReglaService.actualizar({"tolerancia_min": 10, "monto_bono": "0", "max_tardanzas_bono": 0, "tardanzas_alerta": 3,
                                 "faltas_alerta": 2, "vigencia_desde": "2026-12-01"}, rrhh)


def test_nueva_regla_cierra_la_anterior(ctx):
    rrhh = UsuarioRepositorio.por_username("rrhh")
    ReglaService.actualizar({"tolerancia_min": 5, "monto_bono": "200", "max_tardanzas_bono": 1, "tardanzas_alerta": 3,
                             "faltas_alerta": 2, "vigencia_desde": date.today().isoformat()}, rrhh)
    vigentes = ReglaRepositorio.listar(vigente=True)
    assert len(vigentes) == 1 and vigentes[0].monto_bono == Decimal("200")


# ---------- CU11 · Bono ----------
def test_regla_del_bono():
    regla = SimpleNamespace(max_tardanzas_bono=1, monto_bono=Decimal("150"))
    assert BonoService.evaluar({"TARDANZA": 1}, regla) == (True, Decimal("150"))
    assert BonoService.evaluar({"TARDANZA": 2}, regla)[0] is False
    assert BonoService.evaluar({"FALTA": 1}, regla)[0] is False


# ---------- CU06 · Contingencia ----------
def test_contingencia_rechaza_equipo_no_autorizado(ctx):
    colab = ColaboradorRepositorio.obtener(4)
    with pytest.raises(ErrorNegocio, match="no autorizado"):
        ContingenciaService.registrar_marca(colab, "ENTRADA", "Reloj sin energía", "equipo-desconocido")


def test_contingencia_usa_hora_del_servidor_y_queda_pendiente(ctx):
    colab = ColaboradorRepositorio.obtener(8)
    antes = datetime.now().replace(microsecond=0)
    marca = ContingenciaService.registrar_marca(colab, "SALIDA", "Caída de red", "demo-celular-001")
    assert marca.estado == "PENDIENTE" and marca.origen == "CONTINGENCIA" and marca.fecha_hora >= antes


# ---------- CU05 · Sincronización (con lector simulado del reloj) ----------
def test_sincronizacion_sin_duplicados(ctx):
    ahora = datetime.now().replace(microsecond=0)
    registros = [("101", ahora, "ENTRADA"), ("101", ahora, "ENTRADA"), ("999", ahora, "ENTRADA")]
    log = BiometricoService.sincronizar(1, lector=lambda reloj: registros)[0]
    assert log.estado == "EXITOSA" and log.marcas_descargadas == 1 and "999" in log.mensaje


def test_sincronizacion_registra_error_si_reloj_no_responde(ctx):
    def caido(reloj):
        raise ConnectionError("sin respuesta")
    log = BiometricoService.sincronizar(1, lector=caido)[0]
    assert log.estado == "ERROR" and "no disponible" in log.mensaje


# ---------- CU08 · Validación ----------
def test_rechazo_exige_observacion(ctx):
    sup = UsuarioRepositorio.por_username("supervisor")
    pendientes, _ = ValidacionService.pendientes()
    with pytest.raises(ErrorNegocio, match="motivo"):
        ValidacionService.resolver_marcas([pendientes[0].id_marca], "RECHAZADA", "", sup)
