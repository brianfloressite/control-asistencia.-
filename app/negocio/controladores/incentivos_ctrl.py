"""Controladores del módulo de Liquidación de Bonos y Gestión Disciplinaria: CU10, CU11 y CU12."""
import os
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort
from flask_login import current_user
from app.datos.repositorios import AreaRepositorio, LiquidacionRepositorio, MedidaRepositorio
from app.negocio.seguridad import perfiles, ip_cliente, int_param, RRHH
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.incentivos_service import ReglaService, BonoService, DisciplinaService, TIPOS_MEDIDA

bp = Blueprint("incentivos", __name__)
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


@bp.route("/reglas", methods=["GET", "POST"])
@perfiles(RRHH)
def reglas():
    if request.method == "POST":
        try:
            ReglaService.actualizar(request.form, current_user, ip_cliente())
            flash("Reglas actualizadas: se creó una nueva versión vigente.", "success")
            return redirect(url_for("incentivos.reglas"))
        except ErrorNegocio as e:
            flash(str(e), "danger")
    return render_template("incentivos/reglas.html", regla=ReglaService.vigente(), historial=ReglaService.historial(), hoy=date.today())


@bp.route("/bonos", methods=["GET", "POST"])
@perfiles(RRHH)
def bonos():
    hoy = date.today()
    anio, mes = int_param("anio") or hoy.year, int_param("mes") or hoy.month
    liq, avisos = LiquidacionRepositorio.por_periodo(anio, mes), []
    if request.method == "POST":
        try:
            if request.form.get("accion") == "cerrar":
                liq = BonoService.cerrar(int(request.form["id_liquidacion"]), current_user, ip_cliente())
                flash("Liquidación cerrada.", "success")
            else:
                liq, avisos = BonoService.calcular(anio, mes, current_user, int_param("area"), ip_cliente())
                flash("Cálculo realizado.", "success")
        except ErrorNegocio as e:
            flash(str(e), "danger")
    return render_template("incentivos/bonos.html", liq=liq, avisos=avisos, anio=anio, mes=mes, meses=MESES,
                           areas=AreaRepositorio.listar(estado=True))


@bp.route("/medidas", methods=["GET", "POST"])
@perfiles(RRHH)
def medidas():
    if request.method == "POST":
        try:
            if request.form.get("accion") == "descartar":
                DisciplinaService.descartar(int(request.form["id_alerta"]), request.form.get("motivo"), current_user, ip_cliente())
                flash("Alerta descartada.", "info")
            else:
                med = DisciplinaService.registrar_medida(int(request.form.get("id_alerta") or 0), request.form.get("tipo"),
                                                         request.form.get("sustento"), bool(request.form.get("emitir_pdf")), current_user, ip_cliente())
                flash("Medida registrada" + (" y carta PDF generada." if med.ruta_carta_pdf else "."), "success")
        except ErrorNegocio as e:
            flash(str(e), "danger")
        return redirect(url_for("incentivos.medidas"))
    DisciplinaService.generar_alertas()
    return render_template("incentivos/medidas.html", alertas=DisciplinaService.alertas(), medidas=DisciplinaService.medidas(),
                           tipos=TIPOS_MEDIDA, sel=int_param("alerta"))


@bp.route("/medidas/<int:id_medida>/carta")
@perfiles(RRHH)
def carta(id_medida):
    med = MedidaRepositorio.obtener(id_medida)
    if med is None or not med.ruta_carta_pdf or not os.path.exists(med.ruta_carta_pdf):
        abort(404)
    return send_file(med.ruta_carta_pdf, mimetype="application/pdf", download_name=f"carta_{med.colaborador.dni}.pdf")
