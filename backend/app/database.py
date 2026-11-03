import asyncio
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

logger = logging.getLogger("voice_agent.database")
logging.basicConfig(level=logging.INFO)

Base = declarative_base()

_engine = None
_async_session_maker = None
_active_db_type = "unknown"
_init_lock = asyncio.Lock()


async def init_engine():
    global _engine, _async_session_maker, _active_db_type
    if _engine is not None and _async_session_maker is not None:
        return _engine

    async with _init_lock:
        if _engine is not None and _async_session_maker is not None:
            return _engine

        primary_url = settings.DATABASE_URL
        fallback_url = settings.SQLITE_FALLBACK_URL
        test_engine = None

        # Try primary database (PostgreSQL asyncpg)
        try:
            logger.info(f"Connecting to primary database: {primary_url.split('@')[-1] if '@' in primary_url else primary_url}")
            test_engine = create_async_engine(
                primary_url, 
                echo=False, 
                future=True,
                connect_args={"timeout": 3} if "postgresql" in primary_url else {}
            )
            async with test_engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            
            _engine = test_engine
            _active_db_type = "postgresql" if "postgresql" in primary_url else "custom"
            logger.info("Successfully connected to primary database.")
        except Exception as exc:
            if test_engine is not None:
                try:
                    await test_engine.dispose()
                except Exception:
                    pass

            logger.warning(
                f"Primary database not accessible ({exc}). "
                f"Using local SQLite ({fallback_url}) for immediate zero-config execution."
            )
            _engine = create_async_engine(
                fallback_url, 
                echo=False, 
                future=True,
                connect_args={"check_same_thread": False}
            )
            _active_db_type = "sqlite"

        _async_session_maker = async_sessionmaker(
            _engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )

        # Ensure tables exist
        import app.models  # noqa
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return _engine


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine has not been initialized. Call init_engine() first.")
    return _engine


def get_session_maker():
    if _async_session_maker is None:
        raise RuntimeError("Session maker has not been initialized. Call init_engine() first.")
    return _async_session_maker


def get_db_type() -> str:
    return _active_db_type


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if _engine is None or _async_session_maker is None:
        await init_engine()
    
    async with _async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
