"""CAPA DE NEGOCIO - Servicios (patrón Service Layer).

Cada servicio implementa las reglas de un módulo del sistema y usa los repositorios
de la capa de datos. Los controladores (blueprints) solo llaman a estos servicios.
"""


class ErrorNegocio(Exception):
    """Error de validación de una regla de negocio; su mensaje se muestra al usuario."""
