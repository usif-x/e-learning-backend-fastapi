"""
Gunicorn configuration file for production deployment.
Usage: gunicorn -c gunicorn.conf.py main:app
"""

import multiprocessing
import os
from pathlib import Path

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker processes - OPTIMIZED FOR MEMORY
# Formula: cpu_count + 1 (instead of cpu_count * 2 + 1)
# This reduces memory usage significantly while maintaining good performance
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Aggressive worker recycling to prevent memory leaks
max_requests = 500  # Restart after 500 requests (was 1000)
max_requests_jitter = 50
timeout = 1200  # 20 minutes - increased for long-running AI operations
graceful_timeout = 30
keepalive = 5

# Restart workers more frequently to prevent memory accumulation
max_worker_lifetime = 1800  # 30 minutes (was 1 hour)

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "fastapi-app"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

# Logging configuration
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] %(message)s",
        },
        "access": {
            "format": "%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "gunicorn.error": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
}


# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("=" * 80)
    server.log.info("Starting Gunicorn server...")
    server.log.info(f"Workers: {workers}")
    server.log.info(f"Worker class: {worker_class}")
    server.log.info(f"Binding to: {bind}")
    server.log.info("=" * 80)


def on_reload(server):
    """Called to recycle workers during a reload."""
    server.log.info("Reloading workers...")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("✓ Server is ready. Accepting connections.")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process...")


def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info(f"Worker received INT or QUIT signal (pid: {worker.pid})")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.error(f"Worker received SIGABRT signal (pid: {worker.pid})")


def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("=" * 80)
    server.log.info("Shutting down Gunicorn server...")
    server.log.info("=" * 80)
