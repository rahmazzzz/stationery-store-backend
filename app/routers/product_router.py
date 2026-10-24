
from typing import Annotated
from app.exceptions import NotFoundError

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.container.dependencies import (
    get_current_admin,
    get_database_session,
    get_write_database_session,
)
from app.schemas.product import (
    InventoryResponse,
    InventoryUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService


router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    data: ProductCreate,
    session: Annotated[Session, Depends(get_write_database_session)],
):
    return ProductService(session).create(data)


@router.get("", response_model=list[ProductResponse])
def get_products(
    session: Annotated[Session, Depends(get_database_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category_id: Annotated[int | None, Query(gt=0)] = None,
):
    return ProductService(session).get_all(
        offset=offset,
        limit=limit,
        category_id=category_id,
    )


@router.get("/slug/{slug}", response_model=ProductResponse)
def get_product_by_slug(
    slug: str,
    session: Annotated[Session, Depends(get_database_session)],
):
    product = ProductService(session).get_by_slug(slug)

    if not product.is_active:
        from app.exceptions import NotFoundError
        raise NotFoundError("Product not found.")

    return product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_database_session)],
):
    product = ProductService(session).get_by_id(product_id)

    if not product.is_active:
        raise NotFoundError("Product not found.")

    return product

@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: Annotated[int, Path(gt=0)],
    data: ProductUpdate,
    session: Annotated[Session, Depends(get_write_database_session)],
):
    return ProductService(session).update(product_id, data)


@router.patch("/{product_id}/deactivate", response_model=ProductResponse)
def deactivate_product(
    product_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_write_database_session)],
):
    return ProductService(session).deactivate(product_id)


@router.patch(
    "/{product_id}/inventory",
    response_model=InventoryResponse,
    tags=["Admin - Inventory"],
    dependencies=[Depends(get_current_admin)],
)
def update_product_inventory(
    product_id: Annotated[int, Path(gt=0)],
    data: InventoryUpdate,
    session: Annotated[Session, Depends(get_write_database_session)],
):
    return ProductService(session).update_inventory(
        product_id,
        data.stock_quantity,
    )
