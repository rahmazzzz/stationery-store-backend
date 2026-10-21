
import pytest
from pydantic import ValidationError

from app.schemas.product_image import (
    ProductImageCreate,
    ProductImageResponse,
    ProductImageUpdate,
)


def test_product_image_create_accepts_valid_data() -> None:
    image = ProductImageCreate(
        image_url="https://cdn.example.com/images/sticker.png",
        storage_key="products/sticker.png",
        alt_text="Floral sticker",
        sort_order=1,
        is_primary=True,
        content_type="image/png",
        file_size_bytes=2048,
    )

    assert str(image.image_url) == (
        "https://cdn.example.com/images/sticker.png"
    )
    assert image.storage_key == "products/sticker.png"
    assert image.is_primary is True
    assert image.file_size_bytes == 2048


def test_product_image_create_uses_expected_defaults() -> None:
    image = ProductImageCreate(
        image_url="https://cdn.example.com/images/sticker.png",
        storage_key="products/sticker.png",
    )

    assert image.alt_text is None
    assert image.sort_order == 0
    assert image.is_primary is False
    assert image.content_type is None
    assert image.file_size_bytes is None


def test_product_image_create_trims_storage_key() -> None:
    image = ProductImageCreate(
        image_url="https://cdn.example.com/images/sticker.png",
        storage_key="  products/sticker.png  ",
    )

    assert image.storage_key == "products/sticker.png"


@pytest.mark.parametrize(
    "storage_key",
    ["", "   "],
)
def test_product_image_create_rejects_blank_storage_key(
    storage_key: str,
) -> None:
    with pytest.raises(ValidationError):
        ProductImageCreate(
            image_url="https://cdn.example.com/images/sticker.png",
            storage_key=storage_key,
        )


def test_product_image_create_rejects_invalid_url() -> None:
    with pytest.raises(ValidationError):
        ProductImageCreate(
            image_url="not-a-valid-url",
            storage_key="products/sticker.png",
        )


@pytest.mark.parametrize("sort_order", [-1, -10])
def test_product_image_create_rejects_negative_sort_order(
    sort_order: int,
) -> None:
    with pytest.raises(ValidationError):
        ProductImageCreate(
            image_url="https://cdn.example.com/images/sticker.png",
            storage_key="products/sticker.png",
            sort_order=sort_order,
        )


@pytest.mark.parametrize("file_size_bytes", [0, -1])
def test_product_image_create_rejects_nonpositive_file_size(
    file_size_bytes: int,
) -> None:
    with pytest.raises(ValidationError):
        ProductImageCreate(
            image_url="https://cdn.example.com/images/sticker.png",
            storage_key="products/sticker.png",
            file_size_bytes=file_size_bytes,
        )


def test_product_image_update_accepts_partial_data() -> None:
    update = ProductImageUpdate(alt_text="Updated description")

    assert update.alt_text == "Updated description"
    assert update.sort_order is None
    assert update.is_primary is None


def test_product_image_update_trims_storage_key() -> None:
    update = ProductImageUpdate(
        storage_key="  products/updated.png  ",
    )

    assert update.storage_key == "products/updated.png"


def test_product_image_update_rejects_blank_storage_key() -> None:
    with pytest.raises(ValidationError):
        ProductImageUpdate(storage_key="   ")


def test_product_image_response_supports_model_attributes() -> None:
    from datetime import datetime, timezone

    class ProductImageObject:
        id = 1
        product_id = 10
        image_url = "https://cdn.example.com/images/sticker.png"
        storage_key = "products/sticker.png"
        alt_text = "Floral sticker"
        sort_order = 0
        is_primary = True
        content_type = "image/png"
        file_size_bytes = 2048
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

    response = ProductImageResponse.model_validate(ProductImageObject())

    assert response.id == 1
    assert response.product_id == 10
    assert response.is_primary is True



@pytest.mark.parametrize(
    "field",
    ["image_url", "storage_key", "sort_order", "is_primary"],
)
def test_product_image_update_rejects_null_for_required_fields(
    field: str,
) -> None:
    with pytest.raises(ValidationError):
        ProductImageUpdate.model_validate({field: None})


def test_product_image_update_allows_null_for_optional_fields() -> None:
    update = ProductImageUpdate(
        alt_text=None,
        content_type=None,
        file_size_bytes=None,
    )

    assert update.alt_text is None
    assert update.content_type is None
    assert update.file_size_bytes is None
