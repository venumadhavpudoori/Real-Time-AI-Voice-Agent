import sys
from pathlib import Path

_BACKEND_DIR = str(Path(__file__).resolve().parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import asyncio
import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import init_engine, Base, get_session_maker
from app.models.table import RestaurantTable
from app.models.menu_item import MenuItem
from app.models.reservation import Reservation
from app.models.audit_log import SafetyAuditLog


INITIAL_TABLES = [
    {"table_number": "T-01", "capacity": 2, "min_capacity": 1, "seating_area": "indoor"},
    {"table_number": "T-02", "capacity": 2, "min_capacity": 1, "seating_area": "indoor"},
    {"table_number": "T-03", "capacity": 4, "min_capacity": 2, "seating_area": "indoor"},
    {"table_number": "T-04", "capacity": 4, "min_capacity": 2, "seating_area": "indoor"},
    {"table_number": "T-05", "capacity": 6, "min_capacity": 3, "seating_area": "indoor"},
    {"table_number": "T-06", "capacity": 8, "min_capacity": 4, "seating_area": "indoor"},
    {"table_number": "P-01", "capacity": 2, "min_capacity": 1, "seating_area": "patio"},
    {"table_number": "P-02", "capacity": 4, "min_capacity": 2, "seating_area": "patio"},
    {"table_number": "P-03", "capacity": 6, "min_capacity": 3, "seating_area": "patio"},
    {"table_number": "PR-01", "capacity": 12, "min_capacity": 6, "seating_area": "private_room"}
]

INITIAL_MENU = [
    {
        "name": "Wild Mushroom Risotto",
        "category": "Main",
        "description": "Creamy Arborio rice with wild forest mushrooms and truffle oil",
        "ingredients": "Arborio rice, wild mushrooms, vegetable broth, parmesan, truffle oil, garlic",
        "allergens": "dairy",
        "is_gluten_free": True,
        "is_vegan": False,
        "is_vegetarian": True,
        "is_nut_free": True,
        "price": 26.50
    },
    {
        "name": "Pan-Seared Atlantic Salmon",
        "category": "Main",
        "description": "Fresh Atlantic salmon fillet served with asparagus and lemon-herb butter",
        "ingredients": "Atlantic salmon, asparagus, butter, lemon, olive oil, sea salt",
        "allergens": "fish,dairy",
        "is_gluten_free": True,
        "is_vegan": False,
        "is_vegetarian": False,
        "is_nut_free": True,
        "price": 32.00
    },
    {
        "name": "Thai Coconut Curry (Spicy)",
        "category": "Main",
        "description": "Aromatic red coconut curry with crushed roasted peanuts and jasmine rice",
        "ingredients": "Coconut milk, red curry paste, bell peppers, tofu, crushed peanuts, peanut oil, cilantro",
        "allergens": "peanuts,soy",
        "is_gluten_free": True,
        "is_vegan": True,
        "is_vegetarian": True,
        "is_nut_free": False,
        "price": 22.00
    },
    {
        "name": "Classic Caesar Salad",
        "category": "Appetizer",
        "description": "Crisp romaine lettuce, croutons, parmesan, house-made anchovy dressing",
        "ingredients": "Romaine lettuce, wheat croutons, parmesan, anchovy paste, eggs, Dijon mustard",
        "allergens": "gluten,fish,dairy,eggs",
        "is_gluten_free": False,
        "is_vegan": False,
        "is_vegetarian": False,
        "is_nut_free": True,
        "price": 14.50
    },
    {
        "name": "Heirloom Tomato Bruschetta",
        "category": "Appetizer",
        "description": "Grilled artisan sourdough topped with ripe heirloom tomatoes, basil, and garlic",
        "ingredients": "Artisan sourdough (wheat), heirloom tomatoes, basil, garlic, extra virgin olive oil",
        "allergens": "gluten",
        "is_gluten_free": False,
        "is_vegan": True,
        "is_vegetarian": True,
        "is_nut_free": True,
        "price": 12.00
    },
    {
        "name": "Crispy Calamari Fritti",
        "category": "Appetizer",
        "description": "Lightly breaded squid rings with roasted garlic aioli and lemon wedges",
        "ingredients": "Squid, wheat flour batter, garlic aioli (eggs), lemon",
        "allergens": "shellfish,gluten,eggs",
        "is_gluten_free": False,
        "is_vegan": False,
        "is_vegetarian": False,
        "is_nut_free": True,
        "price": 16.50
    },
    {
        "name": "Decadent Chocolate Lava Cake",
        "category": "Dessert",
        "description": "Warm molten chocolate cake with vanilla bean gelato and almond praline garnish",
        "ingredients": "Dark chocolate, butter, sugar, eggs, wheat flour, whole milk, almond praline",
        "allergens": "dairy,eggs,gluten,tree_nuts",
        "is_gluten_free": False,
        "is_vegan": False,
        "is_vegetarian": True,
        "is_nut_free": False,
        "price": 11.00
    },
    {
        "name": "Mango Passionfruit Sorbet",
        "category": "Dessert",
        "description": "Refreshing artisanal sorbet crafted with tropical Alfonso mangoes and passionfruit",
        "ingredients": "Alfonso mango puree, passionfruit juice, organic cane sugar, spring water",
        "allergens": "none",
        "is_gluten_free": True,
        "is_vegan": True,
        "is_vegetarian": True,
        "is_nut_free": True,
        "price": 9.50
    }
]


async def seed_database(session: AsyncSession):
    """Seed initial tables, menu items, and a demo reservation if empty."""
    # Check tables
    res_tables = await session.execute(select(RestaurantTable))
    existing_tables = res_tables.scalars().all()
    if not existing_tables:
        for t_data in INITIAL_TABLES:
            session.add(RestaurantTable(**t_data))
        await session.commit()

    # Check menu items
    res_menu = await session.execute(select(MenuItem))
    existing_menu = res_menu.scalars().all()
    if not existing_menu:
        for m_data in INITIAL_MENU:
            session.add(MenuItem(**m_data))
        await session.commit()

    # Seed sample reservation if empty
    res_bookings = await session.execute(select(Reservation))
    existing_bookings = res_bookings.scalars().all()
    if not existing_bookings:
        table_query = await session.execute(select(RestaurantTable).where(RestaurantTable.table_number == "T-03"))
        t03 = table_query.scalar_one_or_none()
        table_id = t03.id if t03 else 1

        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        demo_reservation = Reservation(
            confirmation_code="RES-DEMO01",
            customer_name="Alice Smith",
            customer_phone="(555) 234-5678",
            party_size=4,
            reservation_date=tomorrow,
            reservation_time=datetime.time(19, 30),
            duration_minutes=90,
            table_id=table_id,
            dietary_requirements="Severe peanut allergy",
            allergy_level="SEVERE_ANAPHYLAXIS",
            allergen_flags="peanuts",
            special_requests="Anniversary dinner, window view if possible",
            status="CONFIRMED"
        )
        session.add(demo_reservation)

        # Seed sample safety log
        demo_log = SafetyAuditLog(
            event_type="SEVERE_ALLERGY_DETECTED",
            raw_text_preview="Alice Smith booking: Severe peanut allergy",
            sanitized_text="🚨 RED ALERT: GUEST HAS SEVERE/LIFE-THREATENING ALLERGY TO PEANUTS.",
            risk_level="CRITICAL",
            action_taken="ESCALATED_TO_KITCHEN_ALERT"
        )
        session.add(demo_log)
        await session.commit()


async def main():
    engine = await init_engine()
    session_maker = get_session_maker()
    async with session_maker() as session:
        await seed_database(session)
    print("Database initialization and seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
