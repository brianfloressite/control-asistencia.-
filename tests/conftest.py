"""Configuración de pytest: base de datos SQLite en memoria con los datos de demostración."""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.cli import cargar_datos  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    from config import settings
    settings.TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
    settings.TestingConfig.ARCHIVOS_DIR = str(tmp_path / "archivos")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        cargar_datos(demo=True)
    yield app


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield app


def login(app, usuario, clave="Asistencia2026"):
    cliente = app.test_client()
    cliente.post("/login", data={"username": usuario, "password": clave})
    return cliente
