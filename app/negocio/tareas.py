"""Tareas programadas (APScheduler): sincronización automática del reloj biométrico (CU05)."""
from apscheduler.schedulers.background import BackgroundScheduler

planificador = None


def iniciar(app):
    global planificador
    if planificador or not app.config.get("SCHEDULER_ENABLED"):
        return
    from app.negocio.servicios.marcacion_service import BiometricoService

    def sincronizar():
        with app.app_context():
            BiometricoService.sincronizar()

    planificador = BackgroundScheduler(daemon=True)
    planificador.add_job(sincronizar, "interval", minutes=app.config["SYNC_MINUTES"], id="sync_biometrico", max_instances=1)
    planificador.start()
