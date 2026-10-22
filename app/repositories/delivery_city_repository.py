
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.delivery_city import DeliveryCity


class DeliveryCityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, city_id: int) -> DeliveryCity | None:
        return self.db.get(DeliveryCity, city_id)

    def get_by_name(self, name: str) -> DeliveryCity | None:
        statement = select(DeliveryCity).where(
            func.lower(DeliveryCity.name) == name.strip().lower()
        )
        return self.db.scalar(statement)

    def list_all(self) -> list[DeliveryCity]:
        statement = select(DeliveryCity).order_by(DeliveryCity.name)
        return list(self.db.scalars(statement).all())

    def create(self, city: DeliveryCity) -> DeliveryCity:
        self.db.add(city)
        self.db.flush()
        self.db.refresh(city)
        return city

    def update(self, city: DeliveryCity) -> DeliveryCity:
        self.db.flush()
        self.db.refresh(city)
        return city
