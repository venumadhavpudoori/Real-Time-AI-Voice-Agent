from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TableResponse(BaseModel):
    id: int
    table_number: str
    capacity: int
    min_capacity: int
    seating_area: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AvailabilityQuery(BaseModel):
    date: date
    time: time
    party_size: int = Field(gt=0, le=20)
    seating_area: Optional[str] = None


class AvailabilityResult(BaseModel):
    available: bool
    requested_date: date
    requested_time: time
    party_size: int
    matched_table: Optional[TableResponse] = None
    alternative_times: List[str] = Field(default_factory=list)
    message: str


class ReservationCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    customer_phone: str = Field(min_length=7, max_length=30)
    party_size: int = Field(gt=0, le=20)
    reservation_date: date
    reservation_time: time
    seating_area: Optional[str] = "indoor"
    dietary_requirements: Optional[str] = None
    special_requests: Optional[str] = None

    @field_validator("customer_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Customer name must be at least 2 characters.")
        return clean


class ReservationResponse(BaseModel):
    id: int
    confirmation_code: str
    customer_name: str
    customer_phone: str
    party_size: int
    reservation_date: date
    reservation_time: time
    duration_minutes: int
    table_id: Optional[int]
    table: Optional[TableResponse] = None
    dietary_requirements: Optional[str]
    allergy_level: str
    allergen_flags: Optional[str]
    special_requests: Optional[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReservationCancelRequest(BaseModel):
    confirmation_code: str
    customer_phone: Optional[str] = None
