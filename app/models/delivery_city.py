
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DeliveryCity(Base):
    __tablename__ = "delivery_cities"

    __table_args__ = (
        CheckConstraint(
            "shipping_fee >= 0",
            name="ck_delivery_cities_shipping_fee_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    shipping_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
