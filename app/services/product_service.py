
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Enforce product business rules and coordinate repositories."""

    def __init__(self, session: Session) -> None:
        self.products = ProductRepository(session)
        self.categories = CategoryRepository(session)

    def create(self, data: ProductCreate):
        if self.categories.get_by_id(data.category_id) is None:
            raise NotFoundError("Category not found.")

        if self.products.slug_exists(data.slug):
            raise ConflictError("A product with this slug already exists.")

        if self.products.sku_exists(data.sku):
            raise ConflictError("A product with this SKU already exists.")

        try:
            with self.products.session.begin_nested():
                return self.products.create(data)
        except IntegrityError as exc:
            raise ConflictError(
                "The product conflicts with an existing record or database constraint."
            ) from exc

    def get_by_id(self, product_id: int):
        product = self.products.get_by_id(product_id)

        if product is None:
            raise NotFoundError("Product not found.")
        return product
    def update_inventory(self, product_id: int, stock_quantity: int):
        """Update stock without invalidating existing reservations."""
        product = self.get_by_id(product_id)
        session = self.products.session

        try:
            with session.begin_nested():
                if stock_quantity < product.reserved_quantity:
                    raise ValidationError(
                        "Stock quantity cannot be lower than the quantity "
                        "already reserved for orders."
                    )

                product.stock_quantity = stock_quantity
                session.flush()
                session.refresh(product)

        except IntegrityError as exc:
            raise ValidationError(
                "The inventory update violates a database constraint."
            ) from exc

        return product

    def get_by_slug(self, slug: str):
        product = self.products.get_by_slug(slug)

        if product is None:
            raise NotFoundError("Product not found.")

        return product

    def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        category_id: int | None = None,
    ):
        if offset < 0:
            raise ValidationError("Offset must be zero or greater.")

        if not 1 <= limit <= 100:
            raise ValidationError("Limit must be between 1 and 100.")

        return self.products.get_all(
            offset=offset,
            limit=limit,
            category_id=category_id,
            is_active=True,
        )


    def update(self, product_id: int, data: ProductUpdate):
        changes = data.model_dump(exclude_unset=True)

        if not changes:
            raise ValidationError(
            "At least one field must be provided for a product update."
        )

        product = self.get_by_id(product_id)


        if (
            "category_id" in changes
            and self.categories.get_by_id(changes["category_id"]) is None
        ):
            raise NotFoundError("Category not found.")

        if (
            "slug" in changes
            and self.products.slug_exists(changes["slug"], exclude_id=product_id)
        ):
            raise ConflictError("A product with this slug already exists.")

        if (
            "sku" in changes
            and self.products.sku_exists(changes["sku"], exclude_id=product_id)
        ):
            raise ConflictError("A product with this SKU already exists.")

        # Validate the final state, not just the fields in this PATCH request.

        price = changes.get("price", product.price)
        discount_type = changes.get("discount_type", product.discount_type)
        discount_value = changes.get("discount_value", product.discount_value)

        if discount_type == "none":
            if (
                "discount_value" in changes
                and changes["discount_value"] != Decimal("0.00")
            ):
                raise ValidationError(
                    "Discount value must be zero when discount type is none."
                )
            if (
                changes.get("discount_type") == "none"
                and "discount_value" not in changes
            ):
                data = data.model_copy(
                    update={"discount_value": Decimal("0.00")}
                )
                changes["discount_value"] = Decimal("0.00")
                discount_value = Decimal("0.00")

        if discount_type == "percentage" and discount_value > 100:
            raise ValidationError("Percentage discount cannot exceed 100.")

        if discount_type == "fixed" and discount_value > price:
            raise ValidationError(
                "Fixed discount cannot exceed the product price."
            )

        try:
            with self.products.session.begin_nested():
                return self.products.update(product, data)
        except IntegrityError as exc:
            raise ConflictError(
                "The product conflicts with an existing record or database constraint."
            ) from exc


    def deactivate(self, product_id: int):
        """Deactivate a product without deleting its history."""
        product = self.get_by_id(product_id)

        with self.products.session.begin_nested():
            return self.products.deactivate(product)
