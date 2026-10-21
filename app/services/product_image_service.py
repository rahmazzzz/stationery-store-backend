from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.product import Product
from app.models.product_image import ProductImage
from app.repositories.product_image_repository import ProductImageRepository
from app.schemas.product_image import ProductImageCreate, ProductImageUpdate


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

    def delete(self, product_id: int, image_id: int) -> None:
        image = self.get_for_product(product_id, image_id)
        with self.session.begin_nested():
            self.images.delete(image)
