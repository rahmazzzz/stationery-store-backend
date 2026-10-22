
from decimal import Decimal, ROUND_HALF_UP
import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Cart, CartItem, Product
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository


MONEY = Decimal("0.01")


class CartService:
    """Enforce cart business rules and calculate cart totals."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.carts = CartRepository(session)
        self.products = ProductRepository(session)

    @staticmethod
    def calculate_unit_price(product: Product) -> Decimal:
        """Calculate a product's selling price after its discount."""
        price = Decimal(product.price)

        if product.discount_type == "percentage":
            discount = price * Decimal(product.discount_value) / Decimal("100")
            price -= discount
        elif product.discount_type == "fixed":
            price -= Decimal(product.discount_value)

        return price.quantize(MONEY, rounding=ROUND_HALF_UP)

    def get_or_create_cart(
        self,
        *,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> Cart:
        """Retrieve or create a cart for exactly one owner."""
        if bool(customer_id) == bool(guest_token):
            raise ValidationError(
                "Provide either a customer ID or a guest token, but not both."
            )

        cart = (
            self.carts.get_by_customer_id(customer_id)
            if customer_id is not None
            else self.carts.get_by_guest_token(guest_token)
        )

        if cart is not None:
            return cart

        if customer_id is None and guest_token is None:
            raise ValidationError("A cart owner is required.")

        try:
            with self.session.begin_nested():
                return self.carts.create(
                    customer_id=customer_id,
                    guest_token=guest_token,
                )
        except IntegrityError as exc:
            raise ConflictError(
                "The cart could not be created because of a database conflict."
            ) from exc

    def get_cart(
        self,
        *,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> dict:
        """Return a cart with calculated prices and totals."""
        cart = self.get_or_create_cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )

        items = []
        subtotal = Decimal("0.00")
        total_items = 0

        for item in cart.items:
            unit_price = self.calculate_unit_price(item.product)
            line_total = (unit_price * item.quantity).quantize(MONEY)

            items.append(
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                }
            )

            subtotal += line_total
            total_items += item.quantity

        return {
            "id": cart.id,
            "items": items,
            "total_items": total_items,
            "subtotal": subtotal.quantize(MONEY),
        }

    def add_item(
        self,
        *,
        product_id: int,
        quantity: int,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> dict:
        """Add a product or increase its existing quantity."""
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        product = self.products.get_by_id(product_id)

        if product is None or not product.is_active:
            raise NotFoundError("Active product not found.")

        cart = self.get_or_create_cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )

        item = self.carts.get_item(cart.id, product_id)

        try:
            with self.session.begin_nested():
                if item is None:
                    self.carts.add_item(cart.id, product_id, quantity)
                else:
                    self.carts.update_item_quantity(
                        item,
                        item.quantity + quantity,
                    )
        except IntegrityError as exc:
            raise ConflictError(
                "The cart item could not be saved because of a database conflict."
            ) from exc

        return self.get_cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )

    def update_item(
        self,
        *,
        product_id: int,
        quantity: int,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> dict:
        """Set the quantity of a product already in the cart."""
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        cart = self.get_or_create_cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )
        item = self.carts.get_item(cart.id, product_id)

        if item is None:
            raise NotFoundError("Cart item not found.")

        product = self.products.get_by_id(product_id)
        if product is None or not product.is_active:
            raise NotFoundError("Active product not found.")

        with self.session.begin_nested():
            self.carts.update_item_quantity(item, quantity)

        return self.get_cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )

    def remove_item(
        self,
        *,
        product_id: int,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> dict:
        """Remove a product from the cart."""
        cart = self.get_or_create_cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )
        item = self.carts.get_item(cart.id, product_id)

        if item is None:
            raise NotFoundError("Cart item not found.")

        with self.session.begin_nested():
            self.carts.delete_item(item)

        return self.get_cart(
            customer_id=customer_id,
            guest_token=guest_token,
        )
