from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.product_image import ProductImage


class Product(Base):
    __tablename__ = "products"


    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="ck_products_price_positive",
        ),
        CheckConstraint(
            "width_cm > 0 AND height_cm > 0",
            name="ck_products_dimensions_positive",
        ),
        CheckConstraint(
            "discount_value >= 0",
            name="ck_products_discount_nonnegative",
        ),
        CheckConstraint(
            "discount_type IN ('none', 'percentage', 'fixed')",
            name="ck_products_discount_type",
        ),
        CheckConstraint(
            "discount_type != 'percentage' OR discount_value <= 100",
            name="ck_products_percentage_max_100",
        ),
        CheckConstraint(
            "discount_type != 'fixed' OR discount_value <= price",
            name="ck_products_fixed_discount_max_price",
        ),
        CheckConstraint(
            "discount_type != 'none' OR discount_value = 0",
            name="ck_products_no_discount_value_when_none",
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_products_stock_quantity_non_negative",
        ),
        CheckConstraint(
            "reserved_quantity >= 0",
            name="ck_products_reserved_quantity_non_negative",
        ),
        CheckConstraint(
           "reserved_quantity <= stock_quantity",
           name="ck_products_reserved_not_above_stock",
        ),
    )

     # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Category relationship
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    category: Mapped["Category"] = relationship(
        back_populates="products",
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductImage.sort_order",
    )

    # Product information
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        unique=True,
        nullable=False,
        index=True,
    )

    sku: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Physical dimensions, in centimeters
    width_cm: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        nullable=False,
    )

    height_cm: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        nullable=False,
    )

    # Original price
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # Discount configuration
    discount_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="none",
        server_default="none",
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )

    # Product visibility
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
