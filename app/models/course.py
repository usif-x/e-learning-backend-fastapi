# app/models/course.py
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)

    # Basic Info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    image = Column(Text, nullable=True)  # Course image path

    # Pricing
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    price_before_discount = Column(Numeric(10, 2), nullable=True)

    # Category relationship
    category_id = Column(
        Integer, ForeignKey("categories.id"), nullable=True, index=True
    )

    # Course Settings/Flags
    is_free = Column(Boolean, default=False, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    prepaidable = Column(Boolean, default=False, nullable=False)
    is_couponable = Column(Boolean, default=True, nullable=False)
    sellable = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<Course(id={self.id}, name='{self.name}', price={self.price})>"
