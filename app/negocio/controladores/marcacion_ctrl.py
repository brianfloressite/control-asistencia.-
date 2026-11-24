"""Controladores de Integración Biométrica (CU05) y Marcado por Contingencia (CU06, CU07)."""
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import current_user, login_required
from app.datos import modelos as m
from app.datos.repositorios import RelojRepositorio, DispositivoRepositorio, ReporteFallaRepositorio, TurnoRepositorio
from app.negocio.seguridad import perfiles, ip_cliente, ADMIN
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.marcacion_service import BiometricoService, ContingenciaService, TIPOS_FALLA
from app.negocio.servicios.reportes_service import SincronizacionConsulta
from app.negocio.servicios.seguridad_service import BitacoraService

bp = Blueprint("marcacion", __name__)
COOKIE = "device_id"


@bp.route("/sincronizacion", methods=["GET", "POST"])
@perfiles(ADMIN)
def sincronizacion():
    if request.method == "POST":
        for log in BiometricoService.sincronizar(int(request.form.get("id_reloj") or 0) or None, usuario=current_user):
            if log.estado == "EXITOSA":
                flash(f"{log.reloj.nombre}: {log.marcas_descargadas} marca(s) nuevas consolidadas.", "success")
            else:
                flash(f"{log.reloj.nombre}: {log.mensaje}. Se reintentará en el siguiente ciclo.", "warning")
        return redirect(url_for("marcacion.sincronizacion"))
    return render_template("sincronizacion/index.html", relojes=RelojRepositorio.listar(), logs=SincronizacionConsulta.historial(),
                           fallas=ReporteFallaRepositorio.recientes(8))


@bp.route("/dispositivos", methods=["GET", "POST"])
@perfiles(ADMIN)
def dispositivos():
    resp_cookie = None
    if request.method == "POST":
        if request.form.get("accion") == "registrar_este":
            ident = request.cookies.get(COOKIE) or uuid.uuid4().hex
            if DispositivoRepositorio.autorizado(ident) is None:
                DispositivoRepositorio.agregar(m.DispositivoAutorizado(nombre=request.form.get("nombre") or "Equipo corporativo",
                                                                       tipo=request.form.get("tipo") or "PC", identificador=ident))
                BitacoraService.registrar(current_user.id_usuario, "AUTORIZAR", "Dispositivos", request.form.get("nombre"), ip_cliente(), commit=False)
                DispositivoRepositorio.guardar()
            resp_cookie = ident
            flash("Este equipo quedó autorizado para el marcado por contingencia.", "success")
        elif request.form.get("accion") == "estado":
            d = DispositivoRepositorio.obtener(int(request.form.get("id")))
            d.activo = not d.activo
            DispositivoRepositorio.guardar()
        resp = make_response(redirect(url_for("marcacion.dispositivos")))
        if resp_cookie:
            resp.set_cookie(COOKIE, resp_cookie, max_age=3600 * 24 * 365 * 3, httponly=True, samesite="Lax")
        return resp
    return render_template("admin/dispositivos.html", dispositivos=DispositivoRepositorio.listar(),
                           este=DispositivoRepositorio.autorizado(request.cookies.get(COOKIE)))


@bp.route("/marcar", methods=["GET", "POST"])
@login_required
def marcar():
    colab = current_user.colaborador
    if request.method == "POST":
        try:
            marca = ContingenciaService.registrar_marca(colab, request.form.get("tipo"), request.form.get("motivo"),
                                                         request.cookies.get(COOKIE), ip_cliente(), current_user)
            flash(f"Marca de {marca.tipo.lower()} registrada a las {marca.fecha_hora:%H:%M:%S}. Queda pendiente de validación.", "success")
            return redirect(url_for("marcacion.marcar"))
        except ErrorNegocio as e:
            flash(str(e), "danger")
    turno = TurnoRepositorio.vigente(colab.id_colaborador, datetime.now().date()) if colab else None
    return render_template("contingencia/marcar.html", ahora=datetime.now(), turno=turno,
                           dispositivo=ContingenciaService.dispositivo_autorizado(request.cookies.get(COOKIE)))


@bp.route("/reportar-falla", methods=["GET", "POST"])
@login_required
def reportar_falla():
    if request.method == "POST":
        try:
            reporte, nuevo = ContingenciaService.reportar_falla(current_user.colaborador, request.form.get("tipo"),
                                                                request.form.get("descripcion"), request.form.get("id_reloj"), ip_cliente(), current_user)
            flash(f"Reporte #{reporte.id_reporte} {'registrado' if nuevo else 'existente: se vinculó su reporte'}. "
                  "El supervisor y el administrador fueron notificados.", "success")
            return redirect(url_for("marcacion.marcar"))
        except ErrorNegocio as e:
            flash(str(e), "danger")
    return render_template("contingencia/falla.html", tipos=TIPOS_FALLA, relojes=RelojRepositorio.activos())
