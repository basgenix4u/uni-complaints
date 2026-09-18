"""Gunicorn configuration for production."""

import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Two per core plus one is the usual starting point for a request-bound
# application. Override where the host is smaller than the default suggests.
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv("WEB_THREADS", "2"))
worker_class = "gthread"

timeout = 60
graceful_timeout = 30
keepalive = 5

# Recycle workers periodically so a slow leak cannot accumulate, with jitter
# so they do not all restart at once.
max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms'

# The application is behind a proxy that terminates TLS.
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
