
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.container.dependencies import (
    get_current_admin,
    get_database_session,
    get_write_database_session,
)
from app.schemas.delivery_city import (
    DeliveryCityCreate,
    DeliveryCityUpdate,
    DeliveryCityResponse,
)
from app.services.delivery_city_service import DeliveryCityService


router = APIRouter(
    prefix="/api/v1/admin/delivery-cities",
    tags=["Admin - Delivery Cities"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/", response_model=list[DeliveryCityResponse])
def list_delivery_cities(
    session: Annotated[Session, Depends(get_write_database_session)],
) -> list[DeliveryCityResponse]:
    """List all delivery cities for administrators."""
    service = DeliveryCityService(session)
    return service.list_cities()


@router.post(
    "/",
    response_model=DeliveryCityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery_city(
    data: DeliveryCityCreate,
    session: Annotated[Session, Depends(get_write_database_session)],
) -> DeliveryCityResponse:
    """Create a delivery city."""
    service = DeliveryCityService(session)
    return service.create_city(data)


@router.patch("/{city_id}", response_model=DeliveryCityResponse)
def update_delivery_city(
    city_id: int,
    data: DeliveryCityUpdate,
    session: Annotated[Session, Depends(get_write_database_session)],
) -> DeliveryCityResponse:
    """Update a delivery city's name, shipping fee, or active status."""
    service = DeliveryCityService(session)
    return service.update_city(city_id, data)


public_router = APIRouter(
    prefix="/api/v1/delivery-cities",
    tags=["Delivery Cities"],
)


@public_router.get("/", response_model=list[DeliveryCityResponse])
def list_active_delivery_cities(
    session: Annotated[Session, Depends(get_database_session)],
) -> list[DeliveryCityResponse]:
    service = DeliveryCityService(session)
    return service.list_active_cities()