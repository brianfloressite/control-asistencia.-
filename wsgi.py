"""Punto de entrada para producción (Gunicorn): gunicorn -c config/gunicorn.conf.py wsgi:app"""
from app import create_app

app = create_app("production")
