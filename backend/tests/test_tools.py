import pytest
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base
from app.models.table import RestaurantTable
from app.models.menu_item import MenuItem
from app.models.reservation import Reservation
from app.services.tool_registry import (
    check_table_availability,
    create_reservation,
    check_dietary_safety,
    cancel_reservation
)


async def get_test_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = session_maker()
    # Seed test tables
    session.add(RestaurantTable(table_number="T-01", capacity=2, seating_area="indoor", is_active=True))
    session.add(RestaurantTable(table_number="T-02", capacity=4, seating_area="indoor", is_active=True))
    # Seed test menu
    session.add(MenuItem(
        name="Peanut Curry", 
        category="Main", 
        ingredients="Peanuts, tofu", 
        allergens="peanuts", 
        is_gluten_free=True, 
        price=20.0
    ))
    session.add(MenuItem(
        name="Steamed Rice", 
        category="Main", 
        ingredients="Jasmine rice, water", 
        allergens="none", 
        is_gluten_free=True, 
        price=5.0
    ))
    await session.commit()
    return engine, session


@pytest.mark.asyncio
async def test_check_table_availability():
    engine, test_db = await get_test_db_session()
    try:
        target_date = datetime.date.today() + datetime.timedelta(days=2)
        target_time = datetime.time(19, 0)

        # Should find table T-02 for 4 guests
        res = await check_table_availability(test_db, target_date, target_time, party_size=4)
        assert res["available"] is True
        assert res["matched_table"]["table_number"] == "T-02"

        # Should fail for party of 10
        res_large = await check_table_availability(test_db, target_date, target_time, party_size=10)
        assert res_large["available"] is False
    finally:
        await test_db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_cancel_reservation():
    engine, test_db = await get_test_db_session()
    try:
        target_date = datetime.date.today() + datetime.timedelta(days=2)
        target_time = datetime.time(18, 30)

        # Create reservation
        booking = await create_reservation(
            db=test_db,
            customer_name="Bob Test",
            customer_phone="555-0199",
            date_val=target_date,
            time_val=target_time,
            party_size=2,
            dietary_requirements="Severe peanut allergy"
        )

        assert booking["success"] is True
        code = booking["confirmation_code"]
        assert code.startswith("RES-")
        assert booking["allergy_level"] == "SEVERE_ANAPHYLAXIS"

        # Cancel reservation
        cancel_res = await cancel_reservation(test_db, code)
        assert cancel_res["success"] is True
        assert "successfully cancelled" in cancel_res["message"]
    finally:
        await test_db.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_dietary_safety_tool():
    engine, test_db = await get_test_db_session()
    try:
        safety = await check_dietary_safety(test_db, "I am severely allergic to peanuts")
        assert safety["has_allergy"] is True
        assert "Peanut Curry" in [d["dish_name"] for d in safety["unsafe_dishes"]]
        assert "Steamed Rice" in safety["safe_dishes"]
    finally:
        await test_db.close()
        await engine.dispose()
