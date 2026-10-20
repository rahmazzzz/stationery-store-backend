
from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    """Fields required to create a category."""

    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120)


class CategoryUpdate(BaseModel):
    """Optional fields for updating a category."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )


class CategoryResponse(BaseModel):
    """Category data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
