"""Controladores del módulo de Auditoría de Asistencia: CU08 y CU09."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from app.datos.repositorios import AreaRepositorio
from app.negocio.seguridad import perfiles, ip_cliente, fecha_param, int_param, inicio_mes, SUPERVISOR
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.auditoria_service import ValidacionService, AsistenciaService

bp = Blueprint("auditoria", __name__)


@bp.route("/validaciones", methods=["GET", "POST"])
@perfiles(SUPERVISOR)
def validaciones():
    if request.method == "POST":
        try:
            if request.form.get("id_justificacion"):
                ValidacionService.resolver_justificacion(int(request.form["id_justificacion"]), request.form.get("decision"),
                                                         request.form.get("observacion"), current_user, ip_cliente())
                flash("Justificación resuelta.", "success")
            else:
                n = ValidacionService.resolver_marcas(request.form.getlist("ids"), request.form.get("decision"),
                                                      request.form.get("observacion"), current_user, ip_cliente())
                flash(f"{n} marca(s) resueltas. La asistencia se recalcula automáticamente.", "success")
        except ErrorNegocio as e:
            flash(str(e), "danger")
        return redirect(url_for("auditoria.validaciones", tab=request.form.get("tab", "marcas")))
    marcas, justificaciones = ValidacionService.pendientes(desde=fecha_param("desde"), hasta=fecha_param("hasta"))
    return render_template("auditoria/validaciones.html", marcas=marcas, justificaciones=justificaciones, tab=request.args.get("tab", "marcas"))


@bp.route("/auditoria", methods=["GET", "POST"])
@perfiles(SUPERVISOR)
def inconsistencias():
    if request.method == "POST":
        try:
            AsistenciaService.observar(int(request.form["id"]), request.form.get("observacion"), request.form.get("accion") == "justificar",
                                       current_user, ip_cliente())
            flash("Inconsistencia actualizada.", "success")
        except ErrorNegocio as e:
            flash(str(e), "danger")
        return redirect(request.referrer or url_for("auditoria.inconsistencias"))
    desde, hasta = fecha_param("desde", inicio_mes()), fecha_param("hasta", date.today())
    tipo = request.args.get("tipo") or None
    try:
        filas = AsistenciaService.auditar(desde, hasta, int_param("area"), tipo)
    except ErrorNegocio as e:
        flash(str(e), "danger")
        filas = []
    totales = {t: sum(1 for f in filas if f.tipo == t) for t in ("TARDANZA", "FALTA", "OMISION", "ABANDONO")}
    return render_template("auditoria/inconsistencias.html", filas=filas, totales=totales, areas=AreaRepositorio.listar(estado=True),
                           desde=desde, hasta=hasta, tipo=tipo)
