"""Configuración de Gunicorn (servidor WSGI de producción). Uso: gunicorn -c config/gunicorn.conf.py wsgi:app"""
import multiprocessing

bind = "127.0.0.1:8000"          # Nginx hace de proxy inverso hacia este puerto
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 60
accesslog = "-"
errorlog = "-"
loglevel = "info"
