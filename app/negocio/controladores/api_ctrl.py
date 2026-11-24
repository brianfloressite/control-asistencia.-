"""API REST v1 (JSON): expone los servicios de negocio a clientes externos o a la vista móvil.

Usa la misma sesión autenticada y el control por perfiles. Las peticiones POST requieren
el encabezado X-CSRFToken (lo envía app.js automáticamente).
"""
from datetime import date
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app.datos.repositorios import ColaboradorRepositorio
from app.negocio.seguridad import perfiles, ip_cliente, fecha_param, int_param, inicio_mes, GERENCIA, RRHH
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.marcacion_service import ContingenciaService
from app.negocio.servicios.reportes_service import DashboardService, HistorialService

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.errorhandler(ErrorNegocio)
def error_negocio(e):
    return jsonify(ok=False, error=str(e)), 422


@bp.get("/salud")
def salud():
    return jsonify(ok=True, servicio="control-asistencia", version="1.0")


@bp.get("/dashboard/indicadores")
@perfiles(GERENCIA, RRHH)
def indicadores():
    hoy = date.today()
    return jsonify(ok=True, datos=DashboardService.indicadores(int_param("anio") or hoy.year, int_param("mes") or hoy.month, int_param("area")))


@bp.get("/colaboradores")
@perfiles(RRHH)
def colaboradores():
    return jsonify(ok=True, datos=[{"id": c.id_colaborador, "dni": c.dni, "nombre": c.nombre_completo, "area": c.area.nombre,
                                    "cargo": c.cargo.nombre, "codigo_biometrico": c.codigo_biometrico}
                                   for c in ColaboradorRepositorio.activos(int_param("area"))])


@bp.get("/mi-asistencia")
@login_required
def mi_asistencia():
    datos = HistorialService.de_colaborador(current_user.colaborador, fecha_param("desde", inicio_mes()), fecha_param("hasta", date.today()))
    return jsonify(ok=True, resumen=datos["resumen"],
                   marcas=[{"fecha_hora": mk.fecha_hora.isoformat(), "tipo": mk.tipo, "origen": mk.origen, "estado": mk.estado} for mk in datos["marcas"]])


@bp.post("/marcas/contingencia")
@login_required
def marca_contingencia():
    body = request.get_json(silent=True) or {}
    marca = ContingenciaService.registrar_marca(current_user.colaborador, body.get("tipo"), body.get("motivo"),
                                                 request.cookies.get("device_id"), ip_cliente(), current_user)
    return jsonify(ok=True, id=marca.id_marca, fecha_hora=marca.fecha_hora.isoformat(), estado=marca.estado), 201
