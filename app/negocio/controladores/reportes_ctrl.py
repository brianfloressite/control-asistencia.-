"""Controladores del módulo de Reportes Gerenciales y Dashboard: CU13, CU14 y CU15."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import current_user, login_required
from app.datos.repositorios import AreaRepositorio, ColaboradorRepositorio
from app.negocio.seguridad import perfiles, ip_cliente, fecha_param, int_param, inicio_mes, GERENCIA, RRHH
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.reportes_service import HistorialService, DashboardService, ReporteService
from app.negocio.servicios.auditoria_service import ValidacionService

bp = Blueprint("reportes", __name__)


@bp.route("/mi-asistencia", methods=["GET", "POST"])
@login_required
def mi_asistencia():
    if request.method == "POST":
        try:
            ValidacionService.presentar_justificacion(int(request.form["id_inconsistencia"]), current_user.colaborador,
                                                      request.form.get("motivo"), current_user, ip_cliente())
            flash("Justificación enviada al supervisor.", "success")
        except ErrorNegocio as e:
            flash(str(e), "danger")
        return redirect(url_for("reportes.mi_asistencia"))
    desde, hasta = fecha_param("desde", inicio_mes()), fecha_param("hasta", date.today())
    datos = None
    try:
        datos = HistorialService.de_colaborador(current_user.colaborador, desde, hasta)
    except ErrorNegocio as e:
        flash(str(e), "warning")
    return render_template("reportes/mi_asistencia.html", datos=datos, desde=desde, hasta=hasta)


@bp.route("/dashboard")
@perfiles(GERENCIA, RRHH)
def dashboard():
    hoy = date.today()
    anio, mes = int_param("anio") or hoy.year, int_param("mes") or hoy.month
    return render_template("dashboard/index.html", ind=DashboardService.indicadores(anio, mes, int_param("area")),
                           anio=anio, mes=mes, areas=AreaRepositorio.listar(estado=True), area=int_param("area"))


@bp.route("/reportes", methods=["GET", "POST"])
@perfiles(GERENCIA, RRHH)
def exportar():
    desde, hasta = fecha_param("desde", inicio_mes()), fecha_param("hasta", date.today())
    tipo = request.values.get("tipo", "asistencia")
    if request.method == "POST":
        try:
            buf, nombre, mime = ReporteService.exportar(tipo, request.form.get("formato", "pdf"), desde, hasta, current_user,
                                                        int_param("area"), int_param("colaborador"), ip_cliente())
            return send_file(buf, mimetype=mime, as_attachment=True, download_name=nombre)
        except ErrorNegocio as e:
            flash(str(e), "warning")
    try:
        cab, filas = ReporteService.datos(tipo, desde, hasta, int_param("area"), int_param("colaborador"))
    except ErrorNegocio as e:
        flash(str(e), "danger")
        cab, filas = [], []
    return render_template("reportes/exportar.html", cab=cab, filas=filas[:12], total=len(filas), tipo=tipo, tipos=ReporteService.TIPOS,
                           desde=desde, hasta=hasta, areas=AreaRepositorio.listar(estado=True), colaboradores=ColaboradorRepositorio.activos())
