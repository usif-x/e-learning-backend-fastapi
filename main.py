import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import click
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

# Import the function to create the bot application
# from app.bot.main import create_bot_app
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.decorator import DBException
from app.core.init import initialize_application
from app.core.limiter import custom_rate_limit_exceeded_handler, limiter
from app.models import *
from app.routers import routes

# Create logs directory first
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)
print(
    f"Logs directory created at: {logs_dir.absolute()}"
)  # Add this to see the actual path

# Create storage directory
storage_dir = Path(__file__).parent / "storage"
storage_dir.mkdir(exist_ok=True)
print(f"Storage directory created at: {storage_dir.absolute()}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            logs_dir / "app.log",  # This will be ./logs/app.log, not /logs/app.log
            mode="a",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
if settings.debug:
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)


# Define lifespan context manager to manage both DB and Bot
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    # --- Startup ---
    try:
        # Initialize Database
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Initialize application (create super admin if needed)
        db = SessionLocal()
        try:
            initialize_application(db)
        finally:
            db.close()

        # # Create and start the bot
        # bot_app = create_bot_app()
        # app.state.bot_app = (
        #     bot_app  # Store bot_app in app state to access it on shutdown
        # )
        # await bot_app.initialize()
        # await bot_app.updater.start_polling()
        # await bot_app.start()
        # logger.info("Telegram Bot has started successfully.")

    except Exception as e:
        logger.error(f"Failed during startup: {e}")
        raise

    yield  # The application is now running

    # --- Shutdown ---
    logger.info("Shutting down application...")
    # bot_app = app.state.bot_app
    # if bot_app.updater.running:
    #     await bot_app.updater.stop()
    # await bot_app.stop()
    # await bot_app.shutdown()
    # logger.info("Telegram Bot has been shut down.")


# Create FastAPI app instance with the new lifespan manager
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    debug=settings.debug,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# --- The rest of your main.py file remains the same ---
# (Middleware, exception handlers, routes, etc.)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)


@app.exception_handler(DBException)
async def db_exception_handler(request: Request, exc: DBException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422, content={"detail": exc.errors(), "body": exc.body}
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error occurred", "type": str(type(exc).__name__)},
    )


@app.get("/")
async def root():
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
    }


@app.get("/health")
@limiter.limit("5/minute")
async def health_check(request: Request):
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": "production" if settings.production else "development",
    }


for router in routes:
    app.include_router(router)

# Mount static files for serving uploaded images
app.mount("/storage", StaticFiles(directory=str(storage_dir)), name="storage")

# --- IMPORTANT CHANGE IN run_server ---


@click.command()
@click.option(
    "--env",
    default="dev",
    type=click.Choice(["dev", "prod"]),
    help="Environment to run the server in",
)
@click.option("--port", default=8000, help="Port to run the server on")
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--workers", default=None, type=int, help="Number of worker processes")
def run_server(env: str, port: int, host: str, workers: int | None):
    """Run the FastAPI server with the specified configuration"""
    is_dev = env == "dev"
    log_level = "debug" if is_dev else "info"
    worker_count = workers or (1 if is_dev else 4)

    logger.info(f"Starting server in {env} mode")
    logger.info(f"Host: {host}, Port: {port}, Workers: {worker_count}")

    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=is_dev,
            workers=worker_count,
            log_level=log_level,
        )
        # REMOVED the main() call from here. The lifespan manager handles it now.
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    run_server()
