from app.api.reservations import router as reservations_router
from app.api.tables import router as tables_router
from app.api.menu import router as menu_router
from app.api.guardrails import router as guardrails_router
from app.api.websocket import router as websocket_router

__all__ = [
    "reservations_router",
    "tables_router",
    "menu_router",
    "guardrails_router",
    "websocket_router"
]

