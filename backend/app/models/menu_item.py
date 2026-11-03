from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric
from app.database import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False)  # Appetizer, Main, Dessert, Beverage
    description = Column(Text, nullable=True)
    ingredients = Column(Text, nullable=False)
    allergens = Column(String(255), default="none", nullable=True)  # Comma-separated (e.g. "peanuts,dairy,gluten")
    is_gluten_free = Column(Boolean, default=False, nullable=False)
    is_vegan = Column(Boolean, default=False, nullable=False)
    is_vegetarian = Column(Boolean, default=False, nullable=False)
    is_nut_free = Column(Boolean, default=True, nullable=False)
    price = Column(Numeric(8, 2), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<MenuItem {self.name} (${self.price}, Allergens: {self.allergens})>"

