
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryRepository:
    """Handle database operations for categories."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: CategoryCreate) -> Category:
        """Create and persist a category."""
        category = Category(**data.model_dump())

        self.session.add(category)
        self.session.flush()
        self.session.refresh(category)

        return category

    def get_by_id(self, category_id: int) -> Category | None:
        """Return a category by its ID, if it exists."""
        return self.session.get(Category, category_id)

    def get_by_slug(self, slug: str) -> Category | None:
        """Return a category by its slug, if it exists."""
        statement = select(Category).where(Category.slug == slug)

        return self.session.scalars(statement).one_or_none()

    def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Category]:
        """Return categories with basic pagination."""
        statement = (
            select(Category)
            .order_by(Category.id)
            .offset(offset)
            .limit(limit)
        )

        return list(self.session.scalars(statement).all())

    def update(
        self,
        category: Category,
        data: CategoryUpdate,
    ) -> Category:
        """Apply provided fields to an existing category."""
        changes = data.model_dump(exclude_unset=True)

        for field, value in changes.items():
            setattr(category, field, value)

        self.session.flush()
        self.session.refresh(category)

        return category

    def delete(self, category: Category) -> None:
        """Delete a category, subject to database constraints."""
        self.session.delete(category)
        self.session.flush()

    
    def name_exists(
        self,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        """Check whether a category name already exists."""
        statement = select(Category.id).where(Category.name == name)

        if exclude_id is not None:
            statement = statement.where(Category.id != exclude_id)

        return self.session.scalar(statement) is not None

    def slug_exists(
        self,
        slug: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        """Check whether a category slug already exists."""
        statement = select(Category.id).where(Category.slug == slug)

        if exclude_id is not None:
            statement = statement.where(Category.id != exclude_id)

        return self.session.scalar(statement) is not None
