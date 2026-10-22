
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


CustomerName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=150),
]

PhoneNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=7, max_length=30),
]

CityName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

DeliveryAddress = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=500),
]


class CheckoutCreate(BaseModel):
    customer_name: CustomerName
    phone_number: PhoneNumber
    city: CityName
    delivery_address: DeliveryAddress
    delivery_instructions: str | None = Field(default=None, max_length=1000)

    payment_method: Literal["cash_on_delivery"] = "cash_on_delivery"


class OrderItemResponse(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    customer_name: str
    phone_number: str
    city: str
    delivery_address: str
    delivery_instructions: str | None
    subtotal: Decimal
    shipping_fee: Decimal
    total: Decimal
    payment_method: str
    status: str
    items: list[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)
