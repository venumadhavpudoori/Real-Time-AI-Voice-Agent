import uuid
import datetime
from datetime import date, time, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.table import RestaurantTable
from app.models.reservation import Reservation
from app.models.menu_item import MenuItem
from app.guardrails.allergen_safety import AllergenSafetyGuardrail

allergen_guard = AllergenSafetyGuardrail()


# Tool definitions for OpenAI Function Calling
TOOLS_METADATA = [
    {
        "type": "function",
        "function": {
            "name": "check_table_availability",
            "description": "Check if a dining table is available for a given date, time, party size, and optional seating area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Reservation date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Reservation time in HH:MM format (e.g. '19:00')"},
                    "party_size": {"type": "integer", "description": "Number of guests (1-12)"},
                    "seating_area": {
                        "type": "string", 
                        "enum": ["indoor", "patio", "bar", "private_room"],
                        "description": "Optional seating preference"
                    }
                },
                "required": ["date", "time", "party_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "Book and confirm a restaurant reservation in the database with customer details and dietary/allergy requirements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Full name of the reservation guest"},
                    "customer_phone": {"type": "string", "description": "Phone number of the guest"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Time in HH:MM format"},
                    "party_size": {"type": "integer", "description": "Number of guests"},
                    "seating_area": {"type": "string", "description": "indoor, patio, bar, private_room"},
                    "dietary_requirements": {"type": "string", "description": "Any dietary restrictions or allergies (e.g., 'severe peanut allergy', 'vegan', 'gluten-free')"},
                    "special_requests": {"type": "string", "description": "Birthday, anniversary, quiet table, etc."}
                },
                "required": ["customer_name", "customer_phone", "date", "time", "party_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_dietary_safety",
            "description": "Validate the safety of restaurant menu items against customer allergies or dietary restrictions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dietary_requirements": {"type": "string", "description": "Customer allergies or restrictions"},
                    "dish_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of dish names customer asked about"
                    }
                },
                "required": ["dietary_requirements"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": "Cancel an existing reservation using the confirmation code and customer phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation_code": {"type": "string", "description": "e.g. RES-AB1234"},
                    "customer_phone": {"type": "string", "description": "Optional phone number for verification"}
                },
                "required": ["confirmation_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu_recommendations",
            "description": "Get recommendations from the restaurant menu suitable for specific dietary needs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dietary_requirements": {"type": "string", "description": "e.g. 'gluten-free', 'vegan', 'nut-free'"},
                    "category": {"type": "string", "enum": ["All", "Appetizer", "Main", "Dessert"]}
                }
            }
        }
    }
]


def parse_date_str(d_str: str) -> date:
    try:
        return datetime.date.fromisoformat(d_str)
    except Exception:
        # Default to today or tomorrow if failed
        return datetime.date.today() + datetime.timedelta(days=1)


def parse_time_str(t_str: str) -> time:
    try:
        parts = t_str.split(":")
        return datetime.time(int(parts[0]), int(parts[1]))
    except Exception:
        return datetime.time(19, 0)


async def check_table_availability(
    db: AsyncSession,
    date_val: date,
    time_val: time,
    party_size: int,
    seating_area: Optional[str] = None
) -> Dict[str, Any]:
    """SQL integration to query table occupancy and availability for requested slot."""
    # Find active tables that can accommodate party_size
    stmt = select(RestaurantTable).where(
        RestaurantTable.is_active == True,
        RestaurantTable.capacity >= party_size
    )
    if seating_area and seating_area != "any":
        stmt = stmt.where(RestaurantTable.seating_area == seating_area.lower())

    stmt = stmt.order_by(RestaurantTable.capacity.asc())
    result = await db.execute(stmt)
    suitable_tables = result.scalars().all()

    if not suitable_tables:
        return {
            "available": False,
            "matched_table": None,
            "message": f"Sorry, we do not have tables with capacity for {party_size} guests in the {seating_area or 'requested'} area.",
            "alternative_times": []
        }

    # Standard dining slot window: 90 minutes
    requested_dt = datetime.datetime.combine(date_val, time_val)
    window_start = (requested_dt - timedelta(minutes=89)).time()
    window_end = (requested_dt + timedelta(minutes=89)).time()

    # Query reservations on that date
    res_stmt = select(Reservation).where(
        Reservation.reservation_date == date_val,
        Reservation.status == "CONFIRMED",
        Reservation.reservation_time >= window_start,
        Reservation.reservation_time <= window_end
    )
    res_result = await db.execute(res_stmt)
    active_reservations = res_result.scalars().all()
    occupied_table_ids = {r.table_id for r in active_reservations if r.table_id is not None}

    # Find first non-occupied suitable table
    for table in suitable_tables:
        if table.id not in occupied_table_ids:
            return {
                "available": True,
                "matched_table": {
                    "id": table.id,
                    "table_number": table.table_number,
                    "capacity": table.capacity,
                    "seating_area": table.seating_area
                },
                "requested_date": str(date_val),
                "requested_time": time_val.strftime("%H:%M"),
                "party_size": party_size,
                "message": f"Great news! Table {table.table_number} ({table.seating_area}, seats up to {table.capacity}) is available on {date_val} at {time_val.strftime('%I:%M %p')}."
            }

    # If unavailable at exact time, generate alternatives (+/- 1 hr)
    alt_times = []
    for delta_mins in [-60, -30, 30, 60]:
        alt_dt = requested_dt + timedelta(minutes=delta_mins)
        alt_times.append(alt_dt.strftime("%I:%M %p"))

    return {
        "available": False,
        "matched_table": None,
        "requested_date": str(date_val),
        "requested_time": time_val.strftime("%H:%M"),
        "party_size": party_size,
        "alternative_times": alt_times,
        "message": f"We are fully booked for a party of {party_size} at {time_val.strftime('%I:%M %p')} on {date_val}. Would you like to check {', '.join(alt_times[:2])}?"
    }


async def create_reservation(
    db: AsyncSession,
    customer_name: str,
    customer_phone: str,
    date_val: date,
    time_val: time,
    party_size: int,
    seating_area: Optional[str] = "indoor",
    dietary_requirements: Optional[str] = None,
    special_requests: Optional[str] = None
) -> Dict[str, Any]:
    """SQL integration to insert and confirm a reservation with dietary guardrails."""
    # First, verify availability and find table
    avail = await check_table_availability(db, date_val, time_val, party_size, seating_area)
    if not avail["available"]:
        return {
            "success": False,
            "message": avail["message"],
            "reservation": None
        }

    matched_table_id = avail["matched_table"]["id"]
    table_num = avail["matched_table"]["table_number"]

    # Analyze allergies via guardrail
    allergy_analysis = allergen_guard.analyze_dietary_input(dietary_requirements or "")
    allergy_level = allergy_analysis["allergy_level"]
    allergen_flags = allergy_analysis["allergen_flags_str"]

    # Generate confirmation code: e.g. RES-A12B3
    conf_code = f"RES-{uuid.uuid4().hex[:6].upper()}"

    new_res = Reservation(
        confirmation_code=conf_code,
        customer_name=customer_name,
        customer_phone=customer_phone,
        party_size=party_size,
        reservation_date=date_val,
        reservation_time=time_val,
        duration_minutes=90,
        table_id=matched_table_id,
        dietary_requirements=dietary_requirements,
        allergy_level=allergy_level,
        allergen_flags=allergen_flags,
        special_requests=special_requests,
        status="CONFIRMED"
    )
    db.add(new_res)
    await db.commit()
    await db.refresh(new_res)

    response_data = {
        "success": True,
        "confirmation_code": conf_code,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "party_size": party_size,
        "date": str(date_val),
        "time": time_val.strftime("%I:%M %p"),
        "table_number": table_num,
        "seating_area": avail["matched_table"]["seating_area"],
        "allergy_level": allergy_level,
        "allergen_flags": allergen_flags,
        "kitchen_alert_note": allergy_analysis["kitchen_alert_note"],
        "customer_disclaimer": allergy_analysis["customer_disclaimer"],
        "message": (
            f"Reservation confirmed! Reference {conf_code} for {customer_name}, "
            f"party of {party_size} on {date_val} at {time_val.strftime('%I:%M %p')} at Table {table_num}."
            + (f" {allergy_analysis['customer_disclaimer']}" if allergy_analysis['has_allergy'] else "")
        )
    }
    return response_data


async def check_dietary_safety(
    db: AsyncSession,
    dietary_requirements: str,
    dish_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """SQL integration to assess menu dishes against customer allergy specifications."""
    analysis = allergen_guard.analyze_dietary_input(dietary_requirements)
    customer_allergens = analysis["identified_allergens"]

    stmt = select(MenuItem).where(MenuItem.is_available == True)
    result = await db.execute(stmt)
    all_dishes = result.scalars().all()

    safe_dishes = []
    unsafe_alerts = []

    for dish in all_dishes:
        # Check specific dishes if passed, otherwise check all
        if dish_names:
            normalized_dish_names = [d.lower() for d in dish_names]
            if not any(n in dish.name.lower() for n in normalized_dish_names):
                continue

        has_conflict, conflicts = allergen_guard.check_dish_conflict(dish.allergens, customer_allergens)
        if has_conflict:
            severity = "DANGER" if analysis["allergy_level"] == "SEVERE_ANAPHYLAXIS" else "WARNING"
            unsafe_alerts.append({
                "dish_name": dish.name,
                "conflicting_allergens": conflicts,
                "severity": severity,
                "recommendation": f"Avoid {dish.name}. Contains {', '.join(conflicts)}."
            })
        else:
            safe_dishes.append(dish.name)

    return {
        "dietary_input": dietary_requirements,
        "has_allergy": analysis["has_allergy"],
        "allergy_level": analysis["allergy_level"],
        "identified_allergens": customer_allergens,
        "safe_dishes": safe_dishes,
        "unsafe_dishes": unsafe_alerts,
        "kitchen_alert_note": analysis["kitchen_alert_note"],
        "customer_disclaimer": analysis["customer_disclaimer"],
        "summary": (
            f"Checked {len(all_dishes)} dishes. {len(safe_dishes)} safe options identified. "
            f"{len(unsafe_alerts)} dishes flagged with conflicting allergens."
        )
    }


async def cancel_reservation(
    db: AsyncSession,
    confirmation_code: str,
    customer_phone: Optional[str] = None
) -> Dict[str, Any]:
    """SQL integration to cancel a reservation by reference code."""
    stmt = select(Reservation).where(
        Reservation.confirmation_code == confirmation_code.strip().upper()
    )
    result = await db.execute(stmt)
    res = result.scalar_one_or_none()

    if not res:
        return {
            "success": False,
            "message": f"No active reservation found with confirmation code '{confirmation_code}'."
        }

    if res.status == "CANCELLED":
        return {
            "success": False,
            "message": f"Reservation '{confirmation_code}' is already cancelled."
        }

    res.status = "CANCELLED"
    await db.commit()

    return {
        "success": True,
        "confirmation_code": confirmation_code,
        "customer_name": res.customer_name,
        "message": f"Reservation {confirmation_code} under {res.customer_name} has been successfully cancelled."
    }


async def get_menu_recommendations(
    db: AsyncSession,
    dietary_requirements: Optional[str] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """SQL integration to fetch and filter menu items safely."""
    stmt = select(MenuItem).where(MenuItem.is_available == True)

    if category and category.lower() != "all":
        stmt = stmt.where(MenuItem.category.ilike(category))

    result = await db.execute(stmt)
    dishes = result.scalars().all()

    if dietary_requirements:
        analysis = allergen_guard.analyze_dietary_input(dietary_requirements)
        customer_allergens = analysis["identified_allergens"]
        filtered = []
        for d in dishes:
            has_conflict, _ = allergen_guard.check_dish_conflict(d.allergens, customer_allergens)
            if not has_conflict:
                filtered.append(d)
        dishes = filtered

    return {
        "count": len(dishes),
        "dishes": [
            {
                "id": d.id,
                "name": d.name,
                "category": d.category,
                "description": d.description,
                "price": float(d.price),
                "allergens": d.allergens,
                "is_gluten_free": d.is_gluten_free,
                "is_vegan": d.is_vegan,
                "is_nut_free": d.is_nut_free
            }
            for d in dishes
        ]
    }

