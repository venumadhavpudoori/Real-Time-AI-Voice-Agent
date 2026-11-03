import sys
from pathlib import Path

# Ensure backend root is in sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_engine, Base, get_db_type, get_session_maker
from app.api import (
    reservations_router,
    tables_router,
    menu_router,
    guardrails_router,
    websocket_router
)
from seed_data import seed_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("voice_agent.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and Schema
    logger.info("Starting up Real-Time AI Voice Agent Backend...")
    engine = await init_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schemas verified.")

    # Run Seeding
    session_maker = get_session_maker()
    async with session_maker() as session:
        await seed_database(session)
    logger.info("Initial tables and menu items seeded successfully.")

    yield

    # Shutdown
    logger.info("Shutting down Voice Agent Backend...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-Time AI Voice Agent with Tool Calling, SQL Integration, and Safety Guardrails for Restaurant Reservations",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(reservations_router, prefix="/api")
app.include_router(tables_router, prefix="/api")
app.include_router(menu_router, prefix="/api")
app.include_router(guardrails_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "active_database": get_db_type(),
        "websocket_endpoint": "/ws/voice-agent",
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": get_db_type(),
        "guardrails_enabled": settings.ENABLE_SAFETY_GUARDRAILS,
        "strict_allergy_mode": settings.STRICT_ALLERGY_MODE
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

