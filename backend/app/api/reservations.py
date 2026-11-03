from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.reservation import Reservation
from app.schemas.reservation import (
    ReservationCreate, 
    ReservationResponse, 
    ReservationCancelRequest
)
from app.services.tool_registry import create_reservation, cancel_reservation

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get("", response_model=List[ReservationResponse])
async def list_reservations(
    reservation_date: Optional[date] = Query(None, description="Filter by date"),
    status: Optional[str] = Query(None, description="CONFIRMED, CANCELLED, COMPLETED"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all reservations with optional date and status filters."""
    stmt = select(Reservation).order_by(Reservation.reservation_date.desc(), Reservation.reservation_time.asc())
    if reservation_date:
        stmt = stmt.where(Reservation.reservation_date == reservation_date)
    if status:
        stmt = stmt.where(Reservation.status == status.upper())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ReservationResponse)
async def make_reservation(
    payload: ReservationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new restaurant booking using the safety and SQL tool pipeline."""
    res = await create_reservation(
        db=db,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        date_val=payload.reservation_date,
        time_val=payload.reservation_time,
        party_size=payload.party_size,
        seating_area=payload.seating_area,
        dietary_requirements=payload.dietary_requirements,
        special_requests=payload.special_requests
    )

    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])

    stmt = select(Reservation).where(Reservation.confirmation_code == res["confirmation_code"])
    db_res = await db.execute(stmt)
    return db_res.scalar_one()


@router.get("/{confirmation_code}", response_model=ReservationResponse)
async def get_reservation_by_code(
    confirmation_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Lookup a single reservation by confirmation code."""
    stmt = select(Reservation).where(Reservation.confirmation_code == confirmation_code.strip().upper())
    result = await db.execute(stmt)
    res = result.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found.")
    return res


@router.post("/cancel")
async def cancel_booking(
    payload: ReservationCancelRequest,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a reservation."""
    res = await cancel_reservation(db, payload.confirmation_code, payload.customer_phone)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res

