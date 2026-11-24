"""Control de acceso por perfiles (RNF3) y utilidades comunes de los controladores."""
from datetime import date, datetime
from functools import wraps
from flask import abort, request
from flask_login import current_user, login_required

ADMIN, GERENCIA, RRHH, SUPERVISOR, COLABORADOR = "Administrador", "Gerencia", "RR.HH.", "Supervisor", "Colaborador"


def perfiles(*nombres):
    """Decorador: restringe una ruta a los perfiles indicados (el Administrador accede a todo)."""
    def deco(vista):
        @wraps(vista)
        @login_required
        def envoltura(*args, **kwargs):
            if not (current_user.tiene_perfil(*nombres) or current_user.tiene_perfil(ADMIN)):
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return deco


def ip_cliente():
    return (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()[:45]


def fecha_param(nombre, defecto=None, fuente=None):
    valor = (fuente or request.values).get(nombre)
    if not valor:
        return defecto
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return defecto


def int_param(nombre, fuente=None):
    valor = (fuente or request.values).get(nombre)
    return int(valor) if valor and str(valor).isdigit() else None


def inicio_mes(hoy=None):
    hoy = hoy or date.today()
    return hoy.replace(day=1)
