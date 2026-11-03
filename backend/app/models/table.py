from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(String(10), unique=True, nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    min_capacity = Column(Integer, default=1, nullable=False)
    seating_area = Column(String(50), default="indoor", nullable=False)  # indoor, patio, bar, private_room
    is_active = Column(Boolean, default=True, nullable=False)

    reservations = relationship("Reservation", back_populates="table", lazy="selectin")

    def __repr__(self):
        return f"<RestaurantTable {self.table_number} ({self.seating_area}, cap: {self.capacity})>"

