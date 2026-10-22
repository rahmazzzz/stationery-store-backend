
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


CityName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

ShippingFee = Annotated[
    Decimal,
    Field(ge=0, max_digits=10, decimal_places=2),
]


class DeliveryCityCreate(BaseModel):
    name: CityName
    shipping_fee: ShippingFee


class DeliveryCityUpdate(BaseModel):
    name: CityName | None = None
    shipping_fee: ShippingFee | None = None
    is_active: bool | None = None


class DeliveryCityResponse(BaseModel):
    id: int
    name: str
    shipping_fee: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
