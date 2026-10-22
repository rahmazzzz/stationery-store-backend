
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.order import Order, OrderItem
from app.repositories.cart_repository import CartRepository
from app.services.cart_service import CartService
from app.services.delivery_city_service import DeliveryCityService
from app.schemas.order import CheckoutCreate


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

        # Never trust prices supplied by the client.
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

        # Flush assigns database-generated IDs without committing the
        # transaction. The write-session dependency remains responsible
        # for committing or rolling back the complete operation.
        self.session.flush()

        # Clear the cart only after the order has been created successfully.
        cart.items.clear()
        self.session.flush()

        return order
