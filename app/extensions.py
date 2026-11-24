"""Extensiones compartidas por las tres capas (se inicializan en create_app)."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
bcrypt = Bcrypt()

login_manager.login_view = "auth.login"
login_manager.login_message = "Inicie sesión para continuar."
login_manager.login_message_category = "warning"
