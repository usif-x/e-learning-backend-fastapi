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
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    image = Column(Text, nullable=True)

    price = Column(Numeric(10, 2), nullable=False)
    has_discount = Column(Boolean, default=False, nullable=False)
    discount = Column(Numeric(10, 2), nullable=True)
    is_sellable = Column(Boolean, default=True, nullable=False)

    is_pinned = Column(Boolean, default=False, nullable=False)

    has_relation_with_another_course = Column(Boolean, default=False, nullable=False)
    relation_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    has_certificate = Column(Boolean, default=False, nullable=False)
    is_azhar = Column(Boolean, default=False, nullable=False)
    prepaidable = Column(Boolean, default=False, nullable=False)
    is_free = Column(Boolean, default=False, nullable=False, server_default="false")
    visible_alone = Column(Boolean, default=False, nullable=False)

    study_year = Column(Integer, default=1, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

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
        return f"Course(id={self.id}, title={self.title}, price={self.price})"
