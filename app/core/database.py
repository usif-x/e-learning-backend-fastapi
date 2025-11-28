import logging

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# -----------------------
# Logging setup
# -----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# Database URL
# -----------------------
DATABASE_URL = (
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
        user=settings.db_username,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_database,
    )
)

# Hide password in logs
safe_db_url = DATABASE_URL.replace(settings.db_password, "****")
logger.info(f"Connecting to database: {safe_db_url}")

# -----------------------
# SQLAlchemy engine
# -----------------------
engine = create_engine(
    DATABASE_URL,
    echo=settings.debug,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={"connect_timeout": 5},
)


# -----------------------
# Force Egypt timezone for all connections
# -----------------------
@event.listens_for(engine, "connect")
def set_timezone(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET timezone='Africa/Cairo'")
    cursor.close()


# -----------------------
# Test connection
# -----------------------
try:
    with engine.connect() as conn:
        logger.info("Database connection successful ✅")
except Exception as e:
    logger.error(f"Failed to connect to database ❌: {str(e)}")
    raise

# -----------------------
# Session and Base
# -----------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# -----------------------
# Dependency for FastAPI
# -----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error occurred: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
