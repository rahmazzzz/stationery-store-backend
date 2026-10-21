from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.product import Product
from app.models.product_image import ProductImage
from app.repositories.product_image_repository import ProductImageRepository
from app.schemas.product_image import ProductImageCreate, ProductImageUpdate
from app.clients.storage_client import (
    SupabaseStorageClient,
    get_storage_client,
)


class ProductImageService:
    """Business rules for product-image metadata; no cloud upload yet."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.images = ProductImageRepository(session)

    def _require_product(self, product_id: int) -> Product:
        product = self.session.get(Product, product_id)
        if product is None:
            raise NotFoundError("Product not found.")
        return product

    def get_for_product(self, product_id: int, image_id: int) -> ProductImage:
        self._require_product(product_id)
        image = self.images.get_by_id(image_id)
        if image is None or image.product_id != product_id:
            raise NotFoundError("Product image not found.")
        return image

    def list_for_product(self, product_id: int) -> list[ProductImage]:
        self._require_product(product_id)
        return self.images.get_for_product(product_id)

    def create(self, product_id: int, data: ProductImageCreate) -> ProductImage:
        self._require_product(product_id)
        values = data.model_dump()
        values["image_url"] = str(values["image_url"])
        values["product_id"] = product_id

        if self.images.get_by_storage_key(values["storage_key"]) is not None:
            raise ConflictError("An image with this storage key already exists.")

        try:
            with self.session.begin_nested():
                if values["is_primary"]:
                    self.images.clear_primary_for_product(product_id)
                return self.images.create(values)
        except IntegrityError as exc:
            raise ConflictError(
                "The product image conflicts with an existing record."
            ) from exc

    def update(
        self, product_id: int, image_id: int, data: ProductImageUpdate,
    ) -> ProductImage:
        image = self.get_for_product(product_id, image_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise ValidationError(
                "At least one field must be provided for an image update."
            )

        if "image_url" in changes and changes["image_url"] is not None:
            changes["image_url"] = str(changes["image_url"])
        if "storage_key" in changes:
            existing = self.images.get_by_storage_key(changes["storage_key"])
            if existing is not None and existing.id != image_id:
                raise ConflictError("An image with this storage key already exists.")

        try:
            with self.session.begin_nested():
                if changes.get("is_primary") is True:
                    self.images.clear_primary_for_product(
                        product_id, except_id=image_id,
                    )
                return self.images.update(image, changes)
        except IntegrityError as exc:
            raise ConflictError(
                "The product image conflicts with an existing record."
            ) from exc

    def set_primary(self, product_id: int, image_id: int) -> ProductImage:
        image = self.get_for_product(product_id, image_id)
        with self.session.begin_nested():
            self.images.clear_primary_for_product(product_id, except_id=image_id)
            return self.images.update(image, {"is_primary": True})
    
    @staticmethod
    def _detect_image_type(content: bytes) -> str | None:
        """Detect supported image types from their file signatures."""
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        if (
            len(content) >= 12
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        ):
            return "image/webp"

        return None

    def upload(
        self,
        product_id: int,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        alt_text: str | None = None,
        sort_order: int = 0,
        is_primary: bool = False,
        storage: SupabaseStorageClient | None = None,
    ) -> ProductImage:
        """Upload an image to cloud storage and save its database record."""
        max_size = 10 * 1024 * 1024

        if not content:
            raise ValidationError("The uploaded image cannot be empty.")

        if len(content) > max_size:
            raise ValidationError("Image size must not exceed 10 MB.")

        detected_type = self._detect_image_type(content)

        if detected_type is None:
            raise ValidationError(
                "Unsupported image file. Upload a JPEG, PNG, or WebP image."
            )

        if content_type.lower() != detected_type:
            raise ValidationError(
                "The uploaded file content does not match its declared image type."
            )

        if sort_order < 0:
            raise ValidationError("sort_order must be zero or greater.")

        # Check the product before creating an external storage object.
        self._require_product(product_id)

        storage_client = storage or get_storage_client()

        storage_key, image_url = storage_client.upload(
            product_id=product_id,
            filename=filename,
            content=content,
            content_type=detected_type,
        )

        try:
            return self.create(
                product_id,
                ProductImageCreate(
                    image_url=image_url,
                    storage_key=storage_key,
                    alt_text=alt_text,
                    sort_order=sort_order,
                    is_primary=is_primary,
                    content_type=detected_type,
                    file_size_bytes=len(content),
                ),
            )
        except Exception:
            # Avoid leaving an orphaned cloud file if saving fails.
            try:
                storage_client.delete(storage_key)
            except Exception:
                # Preserve the original database/service error.
                pass
            raise

    def delete(self, product_id: int, image_id: int) -> None:
        image = self.get_for_product(product_id, image_id)
        with self.session.begin_nested():
            self.images.delete(image)
