"""Controladores del módulo de Seguridad y Usuarios: CU01, CU02 y CU16."""
from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.negocio.seguridad import perfiles, ip_cliente, fecha_param, int_param, ADMIN, GERENCIA, RRHH, SUPERVISOR, COLABORADOR
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.seguridad_service import AuthService, UsuarioService, BitacoraService
from app.datos.repositorios import UsuarioRepositorio, ColaboradorRepositorio

bp = Blueprint("auth", __name__)


@bp.route("/")
@login_required
def inicio():
    if current_user.tiene_perfil(ADMIN, GERENCIA, RRHH):
        return redirect(url_for("reportes.dashboard"))
    if current_user.tiene_perfil(SUPERVISOR):
        return redirect(url_for("auditoria.validaciones"))
    return redirect(url_for("reportes.mi_asistencia"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.inicio"))
    if request.method == "POST":
        try:
            usuario = AuthService.autenticar(request.form.get("username"), request.form.get("password"), ip_cliente())
            login_user(usuario)
            return redirect(request.args.get("next") if (request.args.get("next") or "").startswith("/") else url_for("auth.inicio"))
        except ErrorNegocio as e:
            flash(str(e), "danger")
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    BitacoraService.registrar(current_user.id_usuario, "LOGOUT", "Seguridad", "Cierre de sesión", ip_cliente())
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/usuarios", methods=["GET", "POST"])
@bp.route("/usuarios/<int:id_usuario>", methods=["GET", "POST"])
@perfiles(ADMIN)
def usuarios(id_usuario=None):
    editar = UsuarioRepositorio.obtener(id_usuario) if id_usuario else None
    if request.method == "POST":
        try:
            UsuarioService.guardar(request.form, current_user, ip_cliente(), id_usuario)
            flash("Usuario guardado correctamente.", "success")
            return redirect(url_for("auth.usuarios"))
        except ErrorNegocio as e:
            flash(str(e), "danger")
    return render_template("usuarios/lista.html", usuarios=UsuarioService.listar(), perfiles=UsuarioService.perfiles(),
                           colaboradores=ColaboradorRepositorio.activos(), editar=editar)


@bp.post("/usuarios/<int:id_usuario>/estado")
@perfiles(ADMIN)
def estado_usuario(id_usuario):
    try:
        UsuarioService.cambiar_estado(id_usuario, request.form.get("estado"), current_user, ip_cliente())
        flash("Estado actualizado.", "success")
    except ErrorNegocio as e:
        flash(str(e), "danger")
    return redirect(url_for("auth.usuarios"))


@bp.route("/bitacora")
@perfiles(ADMIN)
def bitacora():
    desde = fecha_param("desde", date.today() - timedelta(days=7))
    hasta = fecha_param("hasta", date.today())
    pagina = int_param("page") or 1
    try:
        consulta = BitacoraService.consultar(int_param("usuario"), request.args.get("accion") or None, desde, hasta)
    except ErrorNegocio as e:
        flash(str(e), "danger")
        consulta = BitacoraService.consultar(None, None, None, None)
    from app.extensions import db
    pag = consulta.paginate(page=pagina, per_page=15, error_out=False)
    from app.datos.repositorios import BitacoraRepositorio
    return render_template("admin/bitacora.html", pag=pag, usuarios=UsuarioService.listar(), acciones=BitacoraRepositorio.acciones(),
                           desde=desde, hasta=hasta)
