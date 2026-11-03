from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.menu_item import MenuItem
from app.schemas.menu import MenuItemResponse, DietaryCheckRequest, DietarySafetyAssessment
from app.services.tool_registry import check_dietary_safety

router = APIRouter(prefix="/menu", tags=["Menu & Dietary"])


@router.get("", response_model=List[MenuItemResponse])
async def list_menu_items(
    category: Optional[str] = Query(None, description="Appetizer, Main, Dessert, Beverage"),
    is_gluten_free: Optional[bool] = Query(None),
    is_vegan: Optional[bool] = Query(None),
    is_nut_free: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve restaurant menu items with allergen attributes."""
    stmt = select(MenuItem).where(MenuItem.is_available == True)

    if category:
        stmt = stmt.where(MenuItem.category.ilike(category))
    if is_gluten_free is not None:
        stmt = stmt.where(MenuItem.is_gluten_free == is_gluten_free)
    if is_vegan is not None:
        stmt = stmt.where(MenuItem.is_vegan == is_vegan)
    if is_nut_free is not None:
        stmt = stmt.where(MenuItem.is_nut_free == is_nut_free)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/check-dietary-safety", response_model=DietarySafetyAssessment)
async def check_dietary_restrictions(
    payload: DietaryCheckRequest,
    db: AsyncSession = Depends(get_db)
):
    """Analyze customer dietary requirements against the full restaurant menu."""
    return await check_dietary_safety(db, payload.dietary_requirements, payload.dish_names)

