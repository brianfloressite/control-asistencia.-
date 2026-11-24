"""Controladores (Blueprints de Flask): reciben la petición, llaman al servicio y devuelven la vista."""
from app.negocio.controladores import (seguridad_ctrl, personal_ctrl, marcacion_ctrl, auditoria_ctrl, incentivos_ctrl,
                                       reportes_ctrl, api_ctrl)

BLUEPRINTS = [seguridad_ctrl.bp, personal_ctrl.bp, marcacion_ctrl.bp, auditoria_ctrl.bp, incentivos_ctrl.bp, reportes_ctrl.bp, api_ctrl.bp]
