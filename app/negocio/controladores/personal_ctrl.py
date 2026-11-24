"""Controladores del módulo de Gestión de Personal y Turnos: CU03 y CU04."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from app.extensions import db
from app.negocio.seguridad import perfiles, ip_cliente, int_param, RRHH
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.personal_service import ColaboradorService, TurnoService
from app.datos.repositorios import ColaboradorRepositorio

bp = Blueprint("personal", __name__)


@bp.route("/colaboradores")
@perfiles(RRHH)
def colaboradores():
    areas, cargos = ColaboradorService.catalogos()
    q = ColaboradorService.buscar(texto=request.args.get("q"), id_area=int_param("area"), id_cargo=int_param("cargo"),
                                  estado=request.args.get("estado", "ACTIVO") or None)
    pag = q.paginate(page=int_param("page") or 1, per_page=10, error_out=False)
    return render_template("personal/colaboradores.html", pag=pag, areas=areas, cargos=cargos)


@bp.route("/colaboradores/nuevo", methods=["GET", "POST"])
@bp.route("/colaboradores/<int:id_colaborador>", methods=["GET", "POST"])
@perfiles(RRHH)
def colaborador_form(id_colaborador=None):
    colab = ColaboradorRepositorio.obtener(id_colaborador) if id_colaborador else None
    if request.method == "POST":
        try:
            ColaboradorService.guardar(request.form, current_user, ip_cliente(), id_colaborador)
            flash("Colaborador guardado. Su código biométrico queda disponible para la sincronización.", "success")
            return redirect(url_for("personal.colaboradores"))
        except ErrorNegocio as e:
            flash(str(e), "danger")
    areas, cargos = ColaboradorService.catalogos()
    return render_template("personal/colaborador_form.html", c=colab, areas=areas, cargos=cargos,
                           supervisores=ColaboradorRepositorio.activos(), hoy=date.today())


@bp.post("/colaboradores/<int:id_colaborador>/baja")
@perfiles(RRHH)
def baja(id_colaborador):
    try:
        ColaboradorService.dar_baja(id_colaborador, request.form.get("fecha_cese"), request.form.get("motivo"), current_user, ip_cliente())
        flash("Colaborador dado de baja; su historial se conserva.", "success")
    except ErrorNegocio as e:
        flash(str(e), "danger")
    return redirect(url_for("personal.colaboradores"))


@bp.route("/horarios", methods=["GET", "POST"])
@perfiles(RRHH)
def horarios():
    if request.method == "POST":
        try:
            if request.form.get("accion") == "horario":
                TurnoService.crear_horario(request.form, current_user, ip_cliente())
                flash("Horario registrado.", "success")
            else:
                TurnoService.asignar(request.form, current_user, ip_cliente())
                flash("Turno asignado.", "success")
            return redirect(url_for("personal.horarios"))
        except ErrorNegocio as e:
            flash(str(e), "danger")
    return render_template("personal/horarios.html", horarios=TurnoService.horarios(), asignaciones=TurnoService.asignaciones(),
                           colaboradores=ColaboradorRepositorio.activos(), hoy=date.today())
