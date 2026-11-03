import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_engine, get_session_maker
from seed_data import seed_database

_db_seeded = False


async def ensure_db():
    global _db_seeded
    if not _db_seeded:
        await init_engine()
        session_maker = get_session_maker()
        async with session_maker() as session:
            await seed_database(session)
        _db_seeded = True


@pytest.mark.asyncio
async def test_health_endpoint():
    await ensure_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data


@pytest.mark.asyncio
async def test_menu_endpoint():
    await ensure_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/menu")
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        assert len(items) > 0


@pytest.mark.asyncio
async def test_tables_endpoint():
    await ensure_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tables")
        assert response.status_code == 200
        tables = response.json()
        assert isinstance(tables, list)
        assert len(tables) > 0


@pytest.mark.asyncio
async def test_guardrails_test_endpoint():
    await ensure_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"text": "I am deathly allergic to peanuts and peanuts only."}
        response = await client.post("/api/guardrails/test", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["highest_risk"] == "CRITICAL"
        assert data["allergy_analysis"]["allergy_level"] == "SEVERE_ANAPHYLAXIS"
