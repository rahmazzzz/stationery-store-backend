
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Cart, CartItem


class CartRepository:
    """Handle database operations for carts and cart items."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, cart_id: int) -> Cart | None:
        """Return a cart with its items and products, if it exists."""
        statement = (
            select(Cart)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product)
            )
            .where(Cart.id == cart_id)
        )
        return self.session.scalars(statement).one_or_none()

    def get_by_customer_id(self, customer_id: str) -> Cart | None:
        """Return the cart belonging to a customer."""
        statement = (
            select(Cart)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product)
            )
            .where(Cart.customer_id == customer_id)
        )
        return self.session.scalars(statement).one_or_none()

    def get_by_guest_token(self, guest_token: str) -> Cart | None:
        """Return the cart belonging to a guest session."""
        statement = (
            select(Cart)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product)
            )
            .where(Cart.guest_token == guest_token)
        )
        return self.session.scalars(statement).one_or_none()

    def create(
        self,
        *,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> Cart:
        """Create a cart for a customer or guest."""
        cart = Cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )
        self.session.add(cart)
        self.session.flush()
        self.session.refresh(cart)
        return cart

    def get_item(
        self,
        cart_id: int,
        product_id: int,
    ) -> CartItem | None:
        """Return a specific product row within a cart."""
        statement = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
        )
        return self.session.scalars(statement).one_or_none()


    def add_item(
        self,
        cart_id: int,
        product_id: int,
        quantity: int,
     ) -> CartItem:
        item = CartItem(
        cart_id=cart_id,
        product_id=product_id,
        quantity=quantity,
    )
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)

    # Refresh the cart's items collection before it is read again.
        cart = self.session.get(Cart, cart_id)
        if cart is not None:
           self.session.expire(cart, ["items"])

        return item


    def update_item_quantity(
        self,
        item: CartItem,
        quantity: int,
    ) -> CartItem:
        """Set the quantity of an existing cart item."""
        item.quantity = quantity
        self.session.flush()
        self.session.refresh(item)
        return item

    def delete_item(self, item: CartItem) -> None:
        cart = item.cart

        self.session.delete(item)
        self.session.flush()

        # The cart may still hold the deleted item in its loaded
        # relationship collection. Expire it so SQLAlchemy reloads it.
        self.session.expire(cart, ["items"])
