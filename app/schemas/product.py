
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DiscountType = Literal["none", "percentage", "fixed"]


class ProductCreate(BaseModel):
    """Fields accepted when creating a product."""

    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=150)
    slug: str = Field(min_length=1, max_length=180)
    sku: str = Field(min_length=1, max_length=50)
    description: str | None = None

    width_cm: Decimal = Field(gt=0, max_digits=7, decimal_places=2)
    height_cm: Decimal = Field(gt=0, max_digits=7, decimal_places=2)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    discount_type: DiscountType = "none"
    discount_value: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    is_active: bool = True

    @model_validator(mode="after")
    def validate_discount(self) -> "ProductCreate":
        """Ensure discount values match the selected discount type."""
        if (
            self.discount_type == "percentage"
            and self.discount_value > Decimal("100")
        ):
            raise ValueError("Percentage discount cannot exceed 100.")

        if (
            self.discount_type == "fixed"
            and self.discount_value > self.price
        ):
            raise ValueError("Fixed discount cannot exceed product price.")

        return self


class ProductUpdate(BaseModel):
    """Optional fields accepted when updating a product."""

    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    slug: str | None = Field(default=None, min_length=1, max_length=180)
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None

    width_cm: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=7,
        decimal_places=2,
    )
    height_cm: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=7,
        decimal_places=2,
    )
    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )

    discount_type: DiscountType | None = None
    discount_value: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_discount(self) -> "ProductUpdate":
        """Validate discount combinations when both values are supplied."""
        if (
            self.discount_type == "percentage"
            and self.discount_value is not None
            and self.discount_value > Decimal("100")
        ):
            raise ValueError("Percentage discount cannot exceed 100.")

        if (
            self.discount_type == "fixed"
            and self.discount_value is not None
            and self.price is not None
            and self.discount_value > self.price
        ):
            raise ValueError("Fixed discount cannot exceed product price.")

        return self


class ProductResponse(BaseModel):
    """Product data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str
    slug: str
    sku: str
    description: str | None
    width_cm: Decimal
    height_cm: Decimal
    price: Decimal
    discount_type: DiscountType
    discount_value: Decimal
    is_active: bool
