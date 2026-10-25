
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.delivery_city import DeliveryCity
from app.repositories.delivery_city_repository import DeliveryCityRepository
from app.schemas.delivery_city import (
    DeliveryCityCreate,
    DeliveryCityUpdate,
)


class DeliveryCityService:
    def __init__(self, db: Session) -> None:
        self.repository = DeliveryCityRepository(db)

    def get_shipping_fee(self, city_name: str) -> Decimal:
        city = self.repository.get_by_name(city_name)

        if city is None or not city.is_active:
            raise NotFoundError("Delivery is not available in this city.")

        return city.shipping_fee

    def list_cities(self) -> list[DeliveryCity]:
        return self.repository.list_all()

    def create_city(self, data: DeliveryCityCreate) -> DeliveryCity:
        city = DeliveryCity(
            name=data.name,
            shipping_fee=data.shipping_fee,
            is_active=data.is_active,
        )
        return self.repository.create(city)

    def update_city(
        self,
        city_id: int,
        data: DeliveryCityUpdate,
    ) -> DeliveryCity:
        city = self.repository.get_by_id(city_id)

        if city is None:
            raise NotFoundError("Delivery city not found.")

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(city, field, value)

        return self.repository.update(city)

    def list_active_cities(self):
        return [
           city
           for city in self.repository.list_all()
           if city.is_active
    ]