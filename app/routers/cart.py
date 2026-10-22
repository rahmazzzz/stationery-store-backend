import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Response
from sqlalchemy.orm import Session

from app.container.dependencies import (
    CurrentUser,
    get_optional_current_user,
    get_write_database_session,
)
from app.exceptions import NotFoundError
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartResponse
from app.services.cart_service import CartService



router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])

def resolve_cart_owner(
    current_user: CurrentUser | None,
    guest_token: str | None,
    response: Response,
    *,
    create_guest_token: bool,
) -> dict[str, str]:
    """Resolve the cart owner from authentication or a guest token."""
    if current_user is not None:
        return {"customer_id": current_user["user_id"]}

    if guest_token is None:
        if not create_guest_token:
            from app.exceptions import NotFoundError

            raise NotFoundError("Cart not found.")

        guest_token = secrets.token_urlsafe(32)
        response.headers["X-Guest-Token"] = guest_token

    return {"guest_token": guest_token}



@router.get("", response_model=CartResponse)
def get_cart(
    response: Response,
    session: Annotated[Session, Depends(get_write_database_session)],
    current_user: Annotated[
        CurrentUser | None, Depends(get_optional_current_user)
    ],
    guest_token: Annotated[
        str | None,
        Header(alias="X-Guest-Token", min_length=20, max_length=200),
    ] = None,
) -> dict:
    """Retrieve the authenticated customer's or guest's cart."""
    service = CartService(session)

    if current_user is not None:
        return service.get_cart(customer_id=current_user["user_id"])

    if guest_token is None:
        guest_token = secrets.token_urlsafe(32)
        response.headers["X-Guest-Token"] = guest_token

    return service.get_cart(guest_token=guest_token)


@router.post("/items", response_model=CartResponse)
def add_cart_item(
    data: CartItemCreate,
    response: Response,
    session: Annotated[Session, Depends(get_write_database_session)],
    current_user: Annotated[
        CurrentUser | None, Depends(get_optional_current_user)
    ],
    guest_token: Annotated[
        str | None,
        Header(alias="X-Guest-Token", min_length=20, max_length=200),
    ] = None,
) -> dict:
    """Add a product to the authenticated customer's or guest's cart."""
    service = CartService(session)

    if current_user is not None:
        return service.add_item(
            customer_id=current_user["user_id"],
            product_id=data.product_id,
            quantity=data.quantity,
        )

    if guest_token is None:
        guest_token = secrets.token_urlsafe(32)
        response.headers["X-Guest-Token"] = guest_token

    return service.add_item(
        guest_token=guest_token,
        product_id=data.product_id,
        quantity=data.quantity,
    )


@router.patch("/items/{product_id}", response_model=CartResponse)
def update_cart_item(
    product_id: Annotated[int, Path(gt=0)],
    data: CartItemUpdate,
    session: Annotated[Session, Depends(get_write_database_session)],
    current_user: Annotated[
        CurrentUser | None, Depends(get_optional_current_user)
    ],
    guest_token: Annotated[
        str | None,
        Header(alias="X-Guest-Token", min_length=20, max_length=200),
    ] = None,
) -> dict:
    """Replace the quantity of an item in the cart."""
    service = CartService(session)

    if current_user is not None:
        return service.update_item(
            customer_id=current_user["user_id"],
            product_id=product_id,
            quantity=data.quantity,
        )

    if guest_token is None:
        raise NotFoundError("Cart item not found.")

    return service.update_item(
        guest_token=guest_token,
        product_id=product_id,
        quantity=data.quantity,
    )

@router.delete("/items/{product_id}", response_model=CartResponse)
def remove_cart_item(
    product_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_write_database_session)],
    current_user: Annotated[
        CurrentUser | None, Depends(get_optional_current_user)
    ],
    guest_token: Annotated[
        str | None,
        Header(alias="X-Guest-Token", min_length=20, max_length=200),
    ] = None,
) -> dict:
    """Remove a product from the authenticated customer's or guest's cart."""
    service = CartService(session)

    if current_user is not None:
        return service.remove_item(
            customer_id=current_user["user_id"],
            product_id=product_id,
        )

    if guest_token is None:
        raise NotFoundError("Cart item not found.")

    return service.remove_item(
        guest_token=guest_token,
        product_id=product_id,
    )