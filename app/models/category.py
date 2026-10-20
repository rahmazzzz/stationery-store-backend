
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Category(Base):
    __tablename__ = "categories"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Category information
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    # Relationship with products
    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
        passive_deletes=True,
    )
