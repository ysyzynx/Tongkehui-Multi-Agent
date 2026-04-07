import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

logger = logging.getLogger("tongkehui.database")


def _build_engine(url: str):
    engine_kwargs = {
        "pool_pre_ping": True,
    }

    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs.update(
            {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "pool_recycle": settings.DB_POOL_RECYCLE,
            }
        )

    return create_engine(url, **engine_kwargs)


def _is_engine_healthy(db_engine) -> bool:
    try:
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Primary database health check failed: %s", exc)
        return False

db_url = settings.database_url
engine = _build_engine(db_url)

if not db_url.startswith("sqlite") and settings.DB_AUTO_FALLBACK and not _is_engine_healthy(engine):
    fallback_url = settings.LOCAL_FALLBACK_DB_URL.strip() or "sqlite:///./tongkehui.db"
    logger.warning(
        "Primary DB unreachable, fallback to local DB: %s",
        fallback_url,
    )
    engine = _build_engine(fallback_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
