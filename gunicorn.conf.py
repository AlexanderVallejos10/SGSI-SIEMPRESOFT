"""Servidor de producción del SGSI (Gunicorn).

Varios procesos (workers) atienden en paralelo; cada uno tiene varios hilos (threads), así un usuario que
descarga un Excel no bloquea a los demás. PostgreSQL resuelve la concurrencia de datos con transacciones."""

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
# 2 × núcleos + 1 procesos (máximo 9), con 4 hilos cada uno: ~20-36 solicitudes simultáneas en un servidor de 2-4 núcleos.
workers = int(os.environ.get("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 9)))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", 4))
timeout = 60            # una solicitud colgada se corta a los 60 s
graceful_timeout = 30   # al reiniciar, espera que terminen las solicitudes en curso
keepalive = 5
max_requests = 1000     # cada proceso se renueva tras 1000 solicitudes (evita fugas de memoria)
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")
