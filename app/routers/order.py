
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.container.dependencies import (
    CurrentUser,
    get_optional_current_user,
    get_write_database_session,
)
from app.exceptions import ValidationError
from app.schemas.order import CheckoutCreate, OrderResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/v1", tags=["Orders"])


@router.post("/checkout", response_model=OrderResponse, status_code=201)
def checkout(
    data: CheckoutCreate,
    session: Annotated[Session, Depends(get_write_database_session)],
    current_user: Annotated[
        CurrentUser | None, Depends(get_optional_current_user)
    ],
    guest_token: Annotated[
        str | None,
        Header(alias="X-Guest-Token", min_length=20, max_length=200),
    ] = None,
) -> OrderResponse:
    """Create an order from the authenticated customer's or guest's cart."""
    if current_user is not None:
        customer_id = current_user["user_id"]
        resolved_guest_token = None
    else:
        if guest_token is None:
            raise ValidationError(
                "The X-Guest-Token header is required for guest checkout."
            )

        customer_id = None
        resolved_guest_token = guest_token

    service = OrderService(session)
    order = service.checkout(
        data,
        customer_id=customer_id,
        guest_token=resolved_guest_token,
    )

    return OrderResponse.model_validate(order)
