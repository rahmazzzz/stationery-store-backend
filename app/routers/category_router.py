
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.container.dependencies import (
    get_database_session,
    get_write_database_session,
)
from app.models import Category
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.category_service import CategoryService


router = APIRouter(
    prefix="/api/v1/categories",
    tags=["Categories"],
)


ReadSession = Annotated[
    Session,
    Depends(get_database_session),
]

WriteSession = Annotated[
    Session,
    Depends(get_write_database_session),
]


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: CategoryCreate,
    session: WriteSession,
) -> Category:
    """Create a category."""
    return CategoryService(session).create(data)


@router.get(
    "",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
)
def list_categories(
    session: ReadSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Category]:
    """List categories with pagination."""
    return CategoryService(session).get_all(
        offset=offset,
        limit=limit,
    )


@router.get(
    "/slug/{slug}",
    response_model=CategoryResponse,
)
def get_category_by_slug(
    slug: str,
    session: ReadSession,
) -> Category:
    """Retrieve a category by its slug."""
    return CategoryService(session).get_by_slug(slug)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
)
def get_category(
    category_id: Annotated[int, Path(gt=0)],
    session: ReadSession,
) -> Category:
    """Retrieve a category by its ID."""
    return CategoryService(session).get_by_id(category_id)


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    session: WriteSession,
) -> Category:
    """Partially update a category."""
    return CategoryService(session).update(category_id, data)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    category_id: int,
    session: WriteSession,
) -> Response:
    """Delete a category that has no associated products."""
    CategoryService(session).delete(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
