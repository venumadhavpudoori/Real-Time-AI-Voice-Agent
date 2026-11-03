from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class MenuItemResponse(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str] = None
    ingredients: str
    allergens: Optional[str] = None
    is_gluten_free: bool
    is_vegan: bool
    is_vegetarian: bool
    is_nut_free: bool
    price: Decimal
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class DietaryCheckRequest(BaseModel):
    dietary_requirements: str
    dish_names: Optional[List[str]] = None


class AllergenAlertItem(BaseModel):
    dish_name: str
    conflicting_allergens: List[str]
    severity: str  # SAFE, WARNING, DANGER
    recommendation: str


class DietarySafetyAssessment(BaseModel):
    has_allergy: bool
    allergy_level: str  # NONE, MILD, MODERATE, SEVERE_ANAPHYLAXIS
    identified_allergens: List[str]
    safe_dishes: List[str]
    unsafe_dishes: List[AllergenAlertItem]
    kitchen_alert_note: str
    customer_disclaimer: str
