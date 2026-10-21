
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DiscountType = Literal["none", "percentage", "fixed"]


class ProductCreate(BaseModel):
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
        """Validate discount rules when creating a product."""
        if (
            self.discount_type == "none"
            and self.discount_value != Decimal("0.00")
        ):
            raise ValueError(
                "Discount value must be zero when discount type is none."
            )

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

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data):
        """Reject explicit nulls for fields that cannot be null in the DB."""
        if not isinstance(data, dict):
            return data

        non_nullable_fields = {
            "category_id",
            "name",
            "slug",
            "sku",
            "width_cm",
            "height_cm",
            "price",
            "discount_type",
            "discount_value",
            "is_active",
        }

        null_fields = [
            field
            for field in non_nullable_fields
            if field in data and data[field] is None
        ]

        if null_fields:
            raise ValueError(
                f"These fields cannot be null: {', '.join(sorted(null_fields))}."
            )

        return data

    @model_validator(mode="after")
    def validate_discount(self) -> "ProductUpdate":
        """Validate discount combinations supplied in a PATCH request."""
        if (
            self.discount_type == "none"
            and self.discount_value is not None
            and self.discount_value != Decimal("0.00")
        ):
            raise ValueError(
                "Discount value must be zero when discount type is none."
            )

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
