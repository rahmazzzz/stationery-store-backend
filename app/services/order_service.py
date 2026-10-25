
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.repositories.cart_repository import CartRepository
from app.schemas.order import CheckoutCreate
from app.services.cart_service import CartService
from app.services.delivery_city_service import DeliveryCityService


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.cart_repository = CartRepository(session)
        self.delivery_city_service = DeliveryCityService(session)

    def checkout(
        self,
        data: CheckoutCreate,
        *,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> Order:
        """Create an order and reserve its inventory."""

        # A cart must belong to exactly one verified owner.
        if bool(customer_id) == bool(guest_token):
            raise ValidationError(
                "Provide either an authenticated customer or a guest token."
            )

        if customer_id:
            cart = self.cart_repository.get_by_customer_id(customer_id)
        else:
            cart = self.cart_repository.get_by_guest_token(guest_token)

        if cart is None:
            raise NotFoundError("Cart not found.")

        if not cart.items:
            raise ValidationError("Cannot checkout with an empty cart.")

        # Calculate prices on the server; never trust client-supplied prices.
        subtotal = Decimal("0.00")
        order_items: list[OrderItem] = []

        for cart_item in cart.items:
            product = cart_item.product

            if product is None or not product.is_active:
                raise ValidationError(
                    "Your cart contains a product that is no longer available."
                )

            unit_price = CartService.calculate_unit_price(product)
            line_total = unit_price * cart_item.quantity
            subtotal += line_total

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=cart_item.quantity,
                    line_total=line_total,
                )
            )

        shipping_fee = self.delivery_city_service.get_shipping_fee(data.city)
        total = subtotal + shipping_fee

        # Reserve stock atomically, processing products in ID order.
        for cart_item in sorted(
            cart.items,
            key=lambda item: item.product.id,
        ):
            product = cart_item.product
            quantity = cart_item.quantity

            statement = (
                update(Product)
                .where(
                    Product.id == product.id,
                    Product.is_active.is_(True),
                    Product.stock_quantity - Product.reserved_quantity
                    >= quantity,
                )
                .values(
                    reserved_quantity=Product.reserved_quantity + quantity,
                )
                .returning(Product.id)
            )

            reserved_product_id = (
                self.session.execute(statement).scalar_one_or_none()
            )

            if reserved_product_id is None:
                raise ValidationError(
                    f"Insufficient stock for product '{product.name}'."
                )

        order = Order(
            customer_id=customer_id,
            guest_token=guest_token,
            customer_name=data.customer_name,
            phone_number=data.phone_number,
            city=data.city.strip(),
            delivery_address=data.delivery_address,
            delivery_instructions=data.delivery_instructions,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total=total,
            payment_method="cash_on_delivery",
            status="pending",
            items=order_items,
        )

        self.session.add(order)

        # Flush assigns generated IDs without committing the transaction.
        self.session.flush()

        # Clear the cart only after successfully creating the order.
        cart.items.clear()
        self.session.flush()

        return order

    def cancel_order(
        self,
        order_id: int,
        *,
        customer_id: str | None = None,
        guest_token: str | None = None,
    ) -> Order:
        """Cancel a pending order and release its reserved inventory."""

        if bool(customer_id) == bool(guest_token):
            raise ValidationError(
                "Provide either an authenticated customer or a guest token."
            )

        # Lock the order so concurrent cancellation attempts are serialized.
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
            .with_for_update()
        )

        if customer_id:
            statement = statement.where(Order.customer_id == customer_id)
        else:
            statement = statement.where(Order.guest_token == guest_token)

        order = self.session.execute(statement).scalar_one_or_none()

        if order is None:
            raise NotFoundError("Order not found.")

        if order.status != "pending":
            raise ConflictError("Only pending orders can be cancelled.")

        # Aggregate quantities so each product is updated only once.
        quantities_by_product: dict[int, int] = {}

        for item in order.items:
            if item.product_id is None:
                raise ConflictError(
                    "The order contains a product that cannot be restored."
                )

            quantities_by_product[item.product_id] = (
                quantities_by_product.get(item.product_id, 0) + item.quantity
            )

        # Release reservations atomically, in a consistent product order.
        for product_id, quantity in sorted(quantities_by_product.items()):
            statement = (
                update(Product)
                .where(
                    Product.id == product_id,
                    Product.reserved_quantity >= quantity,
                )
                .values(
                    reserved_quantity=Product.reserved_quantity - quantity,
                )
                .returning(Product.id)
            )

            released_product_id = (
                self.session.execute(statement).scalar_one_or_none()
            )

            if released_product_id is None:
                raise ConflictError(
                    "Inventory could not be released safely."
                )

        order.status = "cancelled"
        self.session.flush()

        # The write-session dependency commits or rolls back the whole operation.
        return order
