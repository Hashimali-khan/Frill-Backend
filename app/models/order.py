import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Order(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "orders"

    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    province: Mapped[str] = mapped_column(String)
    postal_code: Mapped[str] = mapped_column(String)
    payment_method: Mapped[str] = mapped_column(String)
    wallet_number: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    total: Mapped[float] = mapped_column(Numeric(10, 2))

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base, UUIDPKMixin):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name_snapshot: Mapped[str] = mapped_column(String)
    price_snapshot: Mapped[float] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    selected_size: Mapped[str] = mapped_column(String)
    selected_color_name: Mapped[str] = mapped_column(String)
    selected_color_hex: Mapped[str] = mapped_column(String)
    selected_view_label: Mapped[str | None] = mapped_column(String, nullable=True)
    mockup_url: Mapped[str | None] = mapped_column(String, nullable=True)
    print_url: Mapped[str | None] = mapped_column(String, nullable=True)
    design_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")