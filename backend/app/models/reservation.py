from datetime import datetime, timezone, date, time
from sqlalchemy import Column, Integer, String, Text, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    confirmation_code = Column(String(20), unique=True, nullable=False, index=True)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(30), nullable=False)
    party_size = Column(Integer, nullable=False)
    reservation_date = Column(Date, nullable=False, index=True)
    reservation_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=90, nullable=False)
    table_id = Column(Integer, ForeignKey("restaurant_tables.id", ondelete="SET NULL"), nullable=True)

    dietary_requirements = Column(Text, nullable=True)
    allergy_level = Column(String(20), default="NONE", nullable=False)  # NONE, MILD, MODERATE, SEVERE_ANAPHYLAXIS
    allergen_flags = Column(String(255), nullable=True)                 # Comma-separated list of identified allergens
    special_requests = Column(Text, nullable=True)
    status = Column(String(20), default="CONFIRMED", nullable=False)    # CONFIRMED, CANCELLED, COMPLETED

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    table = relationship("RestaurantTable", back_populates="reservations", lazy="selectin")

    def __repr__(self):
        return f"<Reservation {self.confirmation_code}: {self.customer_name} ({self.party_size} guests on {self.reservation_date} {self.reservation_time})>"
