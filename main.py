import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import click
import uvicorn
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.decorator import DBException
from app.core.init import initialize_application
from app.core.limiter import custom_rate_limit_exceeded_handler, limiter
from app.models import *
from app.routers import routes

# ============================================================================
# Directory Setup
# ============================================================================
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
STORAGE_DIR = BASE_DIR / "storage"

# Create directories with proper permissions
for directory in [LOGS_DIR, STORAGE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o755)


# ============================================================================
# Logging Configuration
# ============================================================================
def setup_logging():
    """Configure logging for the application."""
    log_level = logging.DEBUG if settings.debug else logging.INFO
    log_format = "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] %(message)s"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOGS_DIR / "app.log",
            mode="a",
            encoding="utf-8",
        ),
    ]

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Suppress verbose third-party logs
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()


# ============================================================================
# Application Lifespan
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("=" * 80)
    logger.info("Starting application...")
    logger.info("=" * 80)

    # Startup
    try:
        # Initialize database
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")

        # Initialize application data
        db = SessionLocal()
        try:
            initialize_application(db)
            logger.info("✓ Application initialized successfully")
        finally:
            db.close()

        # Verify storage setup
        logger.info(f"Storage directory: {STORAGE_DIR.absolute()}")
        logger.info(f"  - Exists: {STORAGE_DIR.exists()}")
        logger.info(f"  - Writable: {os.access(STORAGE_DIR, os.W_OK)}")
        logger.info(f"  - Contents: {len(list(STORAGE_DIR.iterdir()))} items")

        logger.info("✓ Application startup completed successfully")

    except Exception as e:
        logger.error(f"✗ Failed during startup: {e}", exc_info=True)
        raise

    yield  # Application is running

    # Shutdown
    logger.info("=" * 80)
    logger.info("Shutting down application...")
    logger.info("=" * 80)
    logger.info("✓ Application shutdown completed")


# ============================================================================
# FastAPI Application
# ============================================================================
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    debug=settings.debug,
    lifespan=lifespan,
)

# ============================================================================
# Middleware Configuration
# ============================================================================
app.state.limiter = limiter

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(time.time()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ============================================================================
# Exception Handlers
# ============================================================================
@app.exception_handler(DBException)
async def db_exception_handler(request: Request, exc: DBException):
    logger.error(f"Database exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "type": "database_error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    # Serialize errors to make them JSON serializable
    details = []
    for error in exc.errors():
        if isinstance(error, dict):
            details.append(error)
        else:
            details.append({"error": str(error)})
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": details,
            "body": str(exc.body),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"SQLAlchemy error: {type(exc).__name__}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database error occurred",
            "type": str(type(exc).__name__),
        },
    )


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)


# ============================================================================
# Health Check Endpoints
# ============================================================================
@app.get("/")
async def root():
    """Root endpoint with basic application info."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "environment": "production" if settings.production else "development",
    }


@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Detailed health check endpoint."""
    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": time.time(),
        "environment": "production" if settings.production else "development",
        "database": db_status,
        "storage": "healthy" if STORAGE_DIR.exists() else "unhealthy",
    }


# ============================================================================
# Static Files & Routes
# ============================================================================
# Mount static files BEFORE including routers
if STORAGE_DIR.exists() and STORAGE_DIR.is_dir():
    try:
        app.mount(
            "/storage",
            StaticFiles(directory=str(STORAGE_DIR.absolute())),
            name="storage",
        )
        logger.info(f"✓ Static files mounted: /storage -> {STORAGE_DIR.absolute()}")
    except Exception as e:
        logger.error(f"✗ Failed to mount static files: {e}", exc_info=True)
else:
    logger.error(f"✗ Storage directory not found: {STORAGE_DIR.absolute()}")

# Include application routers
for router in routes:
    app.include_router(router)

logger.info(f"✓ Registered {len(routes)} routers")


# ============================================================================
# CLI Commands
# ============================================================================
@click.group()
def cli():
    """FastAPI application management CLI."""
    pass


def run_migrations():
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully")
    except Exception as e:
        print(f"Migration failed: {e}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to run the server on")
@click.option("--reload", is_flag=True, help="Enable auto-reload (development only)")
def dev(host: str, port: int, reload: bool):
    """Run development server with Uvicorn."""
    logger.info("Starting development server...")
    logger.info(f"  - Host: {host}")
    logger.info(f"  - Port: {port}")
    logger.info(f"  - Reload: {reload}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug",
        access_log=True,
    )


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to run the server on")
@click.option("--workers", default=4, help="Number of worker processes")
def prod(host: str, port: int, workers: int):
    """Run production server with Gunicorn."""

    # 1. RUN MIGRATIONS FIRST
    logger.info("Running database migrations...")
    run_migrations()

    logger.info("Starting production server with Gunicorn...")
    logger.info(f"  - Host: {host}")
    logger.info(f"  - Port: {port}")
    logger.info(f"  - Workers: {workers}")

    import subprocess

    cmd = [
        "gunicorn",
        "main:app",
        "--worker-class",
        "uvicorn.workers.UvicornWorker",
        "--workers",
        str(workers),
        "--bind",
        f"{host}:{port}",
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
        "--log-level",
        "info",
        "--timeout",
        "120",
        "--graceful-timeout",
        "30",
        "--keep-alive",
        "5",
    ]

    try:
        # 2. START SERVER (This blocks until the app stops)
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Gunicorn failed to start: {e}")
        raise click.ClickException(str(e))
    except FileNotFoundError:
        logger.error("Gunicorn not found. Install it with: pip install gunicorn")
        raise click.ClickException("Gunicorn not installed")


@cli.command()
def info():
    """Display application information."""
    click.echo(f"Application: {settings.app_name}")
    click.echo(f"Version: {settings.app_version}")
    click.echo(f"Debug Mode: {settings.debug}")
    click.echo(f"Storage Directory: {STORAGE_DIR.absolute()}")
    click.echo(f"Logs Directory: {LOGS_DIR.absolute()}")


if __name__ == "__main__":
    cli()
