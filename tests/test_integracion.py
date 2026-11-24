"""Pruebas de integración: recorren las tres capas (vista → controlador → servicio → repositorio → base de datos)."""
from datetime import date
from tests.conftest import login
from app.datos import modelos as m


def test_login_y_redireccion_por_perfil(app):
    assert login(app, "rrhh").get("/").location.endswith("/dashboard")
    assert login(app, "supervisor").get("/").location.endswith("/validaciones")
    assert login(app, "jperez").get("/").location.endswith("/mi-asistencia")


def test_rutas_protegidas_por_perfil(app):
    colaborador = login(app, "jperez")
    assert colaborador.get("/dashboard").status_code == 403
    assert colaborador.get("/usuarios").status_code == 403
    assert app.test_client().get("/colaboradores").status_code == 302  # sin sesión → login


def test_todas_las_pantallas_responden(app):
    admin = login(app, "admin")
    for url in ["/usuarios", "/bitacora", "/sincronizacion", "/dispositivos", "/colaboradores", "/colaboradores/nuevo", "/horarios",
                "/validaciones", "/validaciones?tab=justificaciones", "/auditoria", "/reglas", "/bonos", "/medidas", "/dashboard", "/reportes"]:
        assert admin.get(url).status_code == 200, url


def test_flujo_contingencia_validacion_y_bono(app):
    # 1. El colaborador marca por contingencia desde un equipo autorizado (cookie del dispositivo)
    col = login(app, "rmendoza")
    col.set_cookie("device_id", "demo-celular-001")
    r = col.post("/marcar", data={"tipo": "SALIDA", "motivo": "Caída de red"}, follow_redirects=True)
    assert "pendiente de validación" in r.get_data(as_text=True)
    # 2. El supervisor aprueba las marcas pendientes en bloque
    sup = login(app, "supervisor")
    with app.app_context():
        ids = [str(x.id_marca) for x in m.Marca.query.filter_by(estado="PENDIENTE").all()]
    r = sup.post("/validaciones", data={"ids": ids, "decision": "APROBADA"}, follow_redirects=True)
    assert "resueltas" in r.get_data(as_text=True)
    with app.app_context():
        assert m.Marca.query.filter_by(estado="PENDIENTE").count() == 0
        assert m.Validacion.query.count() == len(ids)
    # 3. RR. HH. calcula y cierra el bono del mes
    rrhh = login(app, "rrhh")
    hoy = date.today()
    r = rrhh.post("/bonos", data={"anio": hoy.year, "mes": hoy.month, "accion": "calcular"})
    assert r.status_code == 200
    with app.app_context():
        liq = m.LiquidacionBono.query.filter_by(anio=hoy.year, mes=hoy.month).one()
        assert len(liq.detalles) == m.Colaborador.query.filter_by(estado="ACTIVO").count()
        id_liq = liq.id_liquidacion
    rrhh.post("/bonos", data={"anio": hoy.year, "mes": hoy.month, "accion": "cerrar", "id_liquidacion": id_liq})
    with app.app_context():
        assert db_get(m.LiquidacionBono, id_liq).estado == "CERRADA"


def db_get(modelo, id_):
    from app.extensions import db
    return db.session.get(modelo, id_)


def test_medida_disciplinaria_con_carta_pdf(app):
    rrhh = login(app, "rrhh")
    rrhh.get("/medidas")  # genera alertas según la regla vigente
    with app.app_context():
        alerta = m.AlertaDisciplinaria.query.filter_by(estado="ACTIVA").first()
        assert alerta is not None
        id_alerta = alerta.id_alerta
    rrhh.post("/medidas", data={"id_alerta": id_alerta, "tipo": "AMONESTACION_ESCRITA", "emitir_pdf": "1",
                                "sustento": "Tardanzas reiteradas registradas durante el periodo."})
    with app.app_context():
        medida = m.MedidaDisciplinaria.query.one()
        id_medida = medida.id_medida
    r = rrhh.get(f"/medidas/{id_medida}/carta")
    assert r.status_code == 200 and r.data[:4] == b"%PDF"


def test_exportar_reportes_pdf_y_excel(app):
    rrhh = login(app, "rrhh")
    r = rrhh.post("/reportes", data={"tipo": "asistencia", "formato": "excel"})
    assert r.status_code == 200 and r.data[:2] == b"PK"
    r = rrhh.post("/reportes", data={"tipo": "asistencia", "formato": "pdf"})
    assert r.status_code == 200 and r.data[:4] == b"%PDF"


def test_api_rest(app):
    assert app.test_client().get("/api/v1/salud").get_json()["ok"] is True
    datos = login(app, "rrhh").get("/api/v1/dashboard/indicadores").get_json()
    assert datos["ok"] and 0 <= datos["datos"]["puntualidad"] <= 100
    col = login(app, "jperez")
    col.set_cookie("device_id", "otro-equipo")
    r = col.post("/api/v1/marcas/contingencia", json={"tipo": "ENTRADA", "motivo": "Caída de red"})
    assert r.status_code == 422 and "no autorizado" in r.get_json()["error"]


def test_bitacora_registra_acciones(app):
    login(app, "admin")
    with app.app_context():
        assert m.Bitacora.query.filter_by(accion="LOGIN").count() >= 1
