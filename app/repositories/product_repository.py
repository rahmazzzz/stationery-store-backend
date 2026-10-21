from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    """Handle database operations for products."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: ProductCreate) -> Product:
        """Create and persist a product."""
        product = Product(**data.model_dump())

        self.session.add(product)
        self.session.flush()
        self.session.refresh(product)

        return product

    def get_by_id(self, product_id: int) -> Product | None:
        """Return a product by ID, if it exists."""
        return self.session.get(Product, product_id)

    def get_by_slug(self, slug: str) -> Product | None:
        """Return a product by slug, if it exists."""
        statement = select(Product).where(Product.slug == slug)
        return self.session.scalars(statement).one_or_none()

    def get_by_sku(self, sku: str) -> Product | None:
        """Return a product by SKU, if it exists."""
        statement = select(Product).where(Product.sku == sku)
        return self.session.scalars(statement).one_or_none()

    def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        category_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[Product]:
        """Return filtered products with pagination."""
        statement = select(Product).order_by(Product.id)

        if category_id is not None:
            statement = statement.where(
                Product.category_id == category_id
            )

        if is_active is not None:
            statement = statement.where(
                Product.is_active == is_active
            )

        statement = statement.offset(offset).limit(limit)

        return list(self.session.scalars(statement).all())

    def update(
        self,
        product: Product,
        data: ProductUpdate,
    ) -> Product:
        """Apply supplied fields to an existing product."""
        changes = data.model_dump(exclude_unset=True)

        for field, value in changes.items():
            setattr(product, field, value)

        self.session.flush()
        self.session.refresh(product)

        return product

    def deactivate(self, product: Product) -> Product:
        """Deactivate a product without deleting its history."""
        product.is_active = False

        self.session.flush()
        self.session.refresh(product)

        return product

    def slug_exists(
        self,
        slug: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        """Check whether a slug is already in use."""
        statement = select(Product.id).where(Product.slug == slug)

        if exclude_id is not None:
            statement = statement.where(Product.id != exclude_id)

        return self.session.scalar(statement) is not None

    def sku_exists(
        self,
        sku: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        """Check whether a SKU is already in use."""
        statement = select(Product.id).where(Product.sku == sku)

        if exclude_id is not None:
            statement = statement.where(Product.id != exclude_id)

        return self.session.scalar(statement) is not None
