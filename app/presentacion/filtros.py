"""CAPA DE VISTA - Filtros y variables globales de las plantillas Jinja2 (formato peruano de fechas y montos)."""
from datetime import datetime

ESTADOS = {"ACTIVO": "success", "APROBADA": "success", "EXITOSA": "success", "JUSTIFICADA": "success", "CERRADA": "secondary",
           "PENDIENTE": "warning", "BORRADOR": "warning", "POR_JUSTIFICAR": "warning", "ABIERTO": "warning", "DETECTADA": "info",
           "RECHAZADA": "danger", "ERROR": "danger", "CESADO": "secondary", "INACTIVO": "secondary", "BLOQUEADO": "danger",
           "CONFIRMADA": "danger", "ACTIVA": "danger", "ATENDIDA": "success", "DESCARTADA": "secondary", "REGISTRADA": "info",
           "NOTIFICADA": "primary", "TARDANZA": "warning", "FALTA": "danger", "OMISION": "info", "ABANDONO": "dark",
           "BIOMETRICO": "primary", "CONTINGENCIA": "warning"}

MENU = [
    ("Principal", [("reportes.dashboard", "speedometer2", "Dashboard", ["Gerencia", "RR.HH."]),
                   ("reportes.mi_asistencia", "calendar-check", "Mi asistencia", ["Colaborador", "Supervisor", "RR.HH.", "Gerencia"])]),
    ("Asistencia", [("marcacion.marcar", "phone", "Marcar (contingencia)", ["Colaborador", "Supervisor", "RR.HH.", "Gerencia"]),
                    ("marcacion.reportar_falla", "exclamation-triangle", "Reportar falla", ["Colaborador", "Supervisor", "RR.HH.", "Gerencia"]),
                    ("auditoria.validaciones", "check2-square", "Validaciones", ["Supervisor"]),
                    ("auditoria.inconsistencias", "search", "Auditoría", ["Supervisor"])]),
    ("Personal", [("personal.colaboradores", "people", "Colaboradores", ["RR.HH."]),
                  ("personal.horarios", "clock-history", "Horarios y turnos", ["RR.HH."])]),
    ("Incentivos y sanciones", [("incentivos.reglas", "sliders", "Reglas de negocio", ["RR.HH."]),
                                ("incentivos.bonos", "cash-coin", "Bonos de puntualidad", ["RR.HH."]),
                                ("incentivos.medidas", "file-earmark-text", "Medidas disciplinarias", ["RR.HH."])]),
    ("Reportes", [("reportes.exportar", "file-earmark-arrow-down", "Exportar reportes", ["Gerencia", "RR.HH."])]),
    ("Administración", [("auth.usuarios", "person-gear", "Usuarios y perfiles", []),
                        ("marcacion.sincronizacion", "fingerprint", "Sincronización biométrica", []),
                        ("marcacion.dispositivos", "laptop", "Equipos autorizados", []),
                        ("auth.bitacora", "journal-text", "Bitácora", [])]),
]


def registrar_filtros(app):
    @app.template_filter("f")
    def fecha(v, fmt="%d/%m/%Y"):
        return v.strftime(fmt) if v else "—"

    @app.template_filter("fh")
    def fecha_hora(v):
        return v.strftime("%d/%m/%Y %H:%M") if v else "—"

    @app.template_filter("soles")
    def soles(v):
        return f"S/ {float(v or 0):,.2f}"

    @app.template_filter("badge")
    def badge(v):
        return ESTADOS.get(str(v), "secondary")

    @app.template_filter("titulo")
    def titulo(v):
        return str(v or "").replace("_", " ").capitalize()

    @app.context_processor
    def globales():
        from flask_login import current_user
        menu = []
        if current_user.is_authenticated:
            for seccion, items in MENU:
                vis = [i for i in items if current_user.tiene_perfil("Administrador") or current_user.tiene_perfil(*i[3])]
                if vis:
                    menu.append((seccion, vis))
        return {"MENU": menu, "AHORA": datetime.now()}
