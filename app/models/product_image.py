from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(Base):
    """Metadata for an image stored in cloud object storage."""

    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint(
            "sort_order >= 0",
            name="ck_product_images_sort_order_nonnegative",
        ),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes > 0",
            name="ck_product_images_file_size_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_key: Mapped[str] = mapped_column(
        String(1024), nullable=False, unique=True,
    )
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    product: Mapped["Product"] = relationship(back_populates="images")
