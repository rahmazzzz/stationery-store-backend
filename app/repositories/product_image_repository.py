from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product_image import ProductImage


class ProductImageRepository:
    """Database operations for image metadata. Does not commit transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, values: dict) -> ProductImage:
        image = ProductImage(**values)
        self.session.add(image)
        self.session.flush()
        self.session.refresh(image)
        return image

    def get_by_id(self, image_id: int) -> ProductImage | None:
        return self.session.get(ProductImage, image_id)

    def get_by_storage_key(self, storage_key: str) -> ProductImage | None:
        statement = select(ProductImage).where(
            ProductImage.storage_key == storage_key,
        )
        return self.session.scalar(statement)

    def get_for_product(self, product_id: int) -> list[ProductImage]:
        statement = (
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order, ProductImage.id)
        )
        return list(self.session.scalars(statement).all())

    def update(self, image: ProductImage, changes: dict) -> ProductImage:
        for field, value in changes.items():
            setattr(image, field, value)
        self.session.flush()
        self.session.refresh(image)
        return image

    def delete(self, image: ProductImage) -> None:
        self.session.delete(image)
        self.session.flush()

    def clear_primary_for_product(
        self, product_id: int, *, except_id: int | None = None,
    ) -> None:
        statement = select(ProductImage).where(
            ProductImage.product_id == product_id,
            ProductImage.is_primary.is_(True),
        )
        if except_id is not None:
            statement = statement.where(ProductImage.id != except_id)
        for image in self.session.scalars(statement).all():
            image.is_primary = False
        self.session.flush()
