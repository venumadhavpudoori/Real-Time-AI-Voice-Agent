from typing import List, Optional
from datetime import date, time
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.table import RestaurantTable
from app.schemas.reservation import TableResponse, AvailabilityResult
from app.services.tool_registry import check_table_availability

router = APIRouter(prefix="/tables", tags=["Tables & Availability"])


@router.get("", response_model=List[TableResponse])
async def list_tables(
    seating_area: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List restaurant tables, capacities, and layout areas."""
    stmt = select(RestaurantTable).order_by(RestaurantTable.table_number.asc())
    if seating_area:
        stmt = stmt.where(RestaurantTable.seating_area == seating_area.lower())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/check-availability", response_model=AvailabilityResult)
async def check_availability(
    target_date: date = Query(..., description="Date YYYY-MM-DD"),
    target_time: time = Query(..., description="Time HH:MM"),
    party_size: int = Query(..., ge=1, le=20),
    seating_area: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Check live table availability for a specific party size and time slot."""
    return await check_table_availability(db, target_date, target_time, party_size, seating_area)

