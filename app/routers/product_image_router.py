from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.container.dependencies import (
    get_database_session,
    get_write_database_session,
)
from app.schemas.product_image import (
    ProductImageCreate,
    ProductImageResponse,
    ProductImageUpdate,
)
from app.services.product_image_service import ProductImageService

router = APIRouter(
    prefix="/api/v1/products/{product_id}/images",
    tags=["Product Images"],
)


@router.get("", response_model=list[ProductImageResponse])
def list_product_images(
    product_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_database_session)],
):
    return ProductImageService(session).list_for_product(product_id)


@router.post(
    "",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_image(
    product_id: Annotated[int, Path(gt=0)],
    data: ProductImageCreate,
    session: Annotated[Session, Depends(get_write_database_session)],
):
    return ProductImageService(session).create(product_id, data)


@router.patch("/{image_id}", response_model=ProductImageResponse)
def update_product_image(
    product_id: Annotated[int, Path(gt=0)],
    image_id: Annotated[int, Path(gt=0)],
    data: ProductImageUpdate,
    session: Annotated[Session, Depends(get_write_database_session)],
):
    return ProductImageService(session).update(product_id, image_id, data)


@router.put("/{image_id}/primary", response_model=ProductImageResponse)
def set_primary_product_image(
    product_id: Annotated[int, Path(gt=0)],
    image_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_write_database_session)],
):
    return ProductImageService(session).set_primary(product_id, image_id)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_image(
    product_id: Annotated[int, Path(gt=0)],
    image_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_write_database_session)],
):
    ProductImageService(session).delete(product_id, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
