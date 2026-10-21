from datetime import datetime
from typing import Annotated


from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProductImageCreate(BaseModel):
    image_url: AnyHttpUrl
    storage_key: Annotated[str, Field(min_length=1, max_length=1024)]
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False
    content_type: str | None = Field(default=None, max_length=100)
    file_size_bytes: int | None = Field(default=None, gt=0)

    @field_validator("storage_key")
    @classmethod
    def validate_storage_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("storage_key cannot be blank.")
        return value


class ProductImageUpdate(BaseModel):
    image_url: AnyHttpUrl | None = None
    storage_key: str | None = Field(default=None, min_length=1, max_length=1024)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int | None = Field(default=None, ge=0)
    is_primary: bool | None = None
    content_type: str | None = Field(default=None, max_length=100)
    file_size_bytes: int | None = Field(default=None, gt=0)

    @field_validator("storage_key")
    @classmethod
    def validate_storage_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("storage_key cannot be blank.")

        return value

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data):
        """Reject nulls for fields that cannot be null in the database."""
        if not isinstance(data, dict):
            return data

        non_nullable_fields = {
            "image_url",
            "storage_key",
            "sort_order",
            "is_primary",
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



class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    image_url: str
    storage_key: str
    alt_text: str | None
    sort_order: int
    is_primary: bool
    content_type: str | None
    file_size_bytes: int | None
    created_at: datetime
    updated_at: datetime
