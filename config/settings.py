"""Configuración por entorno. Los valores sensibles se leen de variables de entorno (.env)."""
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-esta-clave-en-produccion")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "mysql+pymysql://asistencia:asistencia@localhost:3306/bd_asistencia?charset=utf8mb4")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Seguridad (RNF3)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    WTF_CSRF_TIME_LIMIT = None
    MAX_INTENTOS_LOGIN = int(os.getenv("MAX_INTENTOS_LOGIN", 5))

    # Integración con el reloj biométrico ZKTeco (RF5)
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    SYNC_MINUTES = int(os.getenv("SYNC_MINUTES", 30))
    ZK_TIMEOUT = int(os.getenv("ZK_TIMEOUT", 5))

    # Archivos generados (cartas PDF de amonestación, evidencias)
    ARCHIVOS_DIR = os.getenv("ARCHIVOS_DIR", os.path.join(BASE_DIR, "instance", "archivos"))
    ITEMS_POR_PAGINA = 15


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "asistencia_dev.db"))


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    SCHEDULER_ENABLED = False
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIGS = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}
