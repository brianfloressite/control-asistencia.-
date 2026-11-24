"""Fábrica de la aplicación (patrón Application Factory).

Estructura en tres capas:
  app/presentacion  → CAPA DE VISTA: plantillas Jinja2 y recursos estáticos (Bootstrap 5, Chart.js)
  app/negocio       → CAPA DE NEGOCIO: controladores (blueprints), servicios y seguridad
  app/datos         → CAPA DE DATOS: modelos ORM y repositorios (MySQL 8 vía SQLAlchemy + PyMySQL)
"""
import os
from flask import Flask, render_template
from config.settings import CONFIGS
from app.extensions import db, migrate, login_manager, csrf, bcrypt


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_CONFIG", "development")
    app = Flask(__name__, template_folder="presentacion/templates", static_folder="presentacion/static",
                instance_relative_config=True)
    app.config.from_object(CONFIGS[config_name])
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(os.path.dirname(app.root_path), "migrations"))
    login_manager.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)

    from app.datos import modelos  # registra los modelos

    @login_manager.user_loader
    def cargar_usuario(id_usuario):
        return db.session.get(modelos.Usuario, int(id_usuario))

    from app.negocio.controladores import BLUEPRINTS
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)

    from app.presentacion.filtros import registrar_filtros
    registrar_filtros(app)

    @app.errorhandler(403)
    def prohibido(e):
        return render_template("errores/error.html", codigo=403, mensaje="No tiene permisos para acceder a esta opción."), 403

    @app.errorhandler(404)
    def no_encontrado(e):
        return render_template("errores/error.html", codigo=404, mensaje="La página solicitada no existe."), 404

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    from app.cli import registrar_comandos
    registrar_comandos(app)

    from app.negocio.tareas import iniciar
    iniciar(app)
    return app
