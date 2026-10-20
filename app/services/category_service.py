
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    """Implement business rules for category management."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = CategoryRepository(session)

    def create(self, data: CategoryCreate) -> Category:
        """Create a category after checking its unique fields."""
        if self._repository.name_exists(data.name):
            raise ConflictError("A category with this name already exists.")

        if self._repository.slug_exists(data.slug):
            raise ConflictError("A category with this slug already exists.")

        try:
            return self._repository.create(data)
        except IntegrityError as exc:
            # Covers uniqueness races between the checks and the insert.
            raise ConflictError(
                "A category with this name or slug already exists."
            ) from exc

    def get_by_id(self, category_id: int) -> Category:
        """Retrieve a category by its ID."""
        category = self._repository.get_by_id(category_id)

        if category is None:
            raise NotFoundError("Category not found.")

        return category

    def get_by_slug(self, slug: str) -> Category:
        """Retrieve a category by its slug."""
        category = self._repository.get_by_slug(slug)

        if category is None:
            raise NotFoundError("Category not found.")

        return category

    def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Category]:
        """Return a paginated list of categories."""
        if offset < 0:
            raise ValueError("Offset cannot be negative.")

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100.")

        return self._repository.get_all(offset=offset, limit=limit)

    def update(
        self,
        category_id: int,
        data: CategoryUpdate,
    ) -> Category:
        """Update a category while preserving uniqueness."""
        category = self.get_by_id(category_id)
        changes = data.model_dump(exclude_unset=True)

        if not changes:
            return category

        if (
            "name" in changes
            and changes["name"] != category.name
            and self._repository.name_exists(
                changes["name"],
                exclude_id=category.id,
            )
        ):
            raise ConflictError("A category with this name already exists.")

        if (
            "slug" in changes
            and changes["slug"] != category.slug
            and self._repository.slug_exists(
                changes["slug"],
                exclude_id=category.id,
            )
        ):
            raise ConflictError("A category with this slug already exists.")

        try:
            return self._repository.update(category, data)
        except IntegrityError as exc:
            raise ConflictError(
                "A category with this name or slug already exists."
            ) from exc

    def delete(self, category_id: int) -> None:
        """Delete a category if database constraints allow it."""
        category = self.get_by_id(category_id)

        try:
            self._repository.delete(category)
        except IntegrityError as exc:
            raise ConflictError(
                "Cannot delete this category because it may contain products."
            ) from exc
