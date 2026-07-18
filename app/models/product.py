import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Product(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "products"

    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    vendor: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String)
    long_description: Mapped[str] = mapped_column(String, default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2))          # Numeric, not Float — exact money math
    old_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    stars: Mapped[float] = mapped_column(Float, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    customizable: Mapped[bool] = mapped_column(Boolean, default=False)
    sizes: Mapped[list[str]] = mapped_column(JSONB, default=list)

    colors: Mapped[list["ProductColor"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

class ProductColor(Base, UUIDPKMixin):
    __tablename__ = "product_colors"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    name: Mapped[str] = mapped_column(String)
    hex: Mapped[str] = mapped_column(String)

    product: Mapped["Product"] = relationship(back_populates="colors")
    views: Mapped[list["ProductView"]] = relationship(
        back_populates="color", cascade="all, delete-orphan"
    )


class ProductView(Base, UUIDPKMixin):
    __tablename__ = "product_views"

    color_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_colors.id"))
    label: Mapped[str] = mapped_column(String)
    image_url: Mapped[str] = mapped_column(String)
    print_area: Mapped[dict] = mapped_column(JSONB)   # {x, y, width, height} — always read/written as one unit

    color: Mapped["ProductColor"] = relationship(back_populates="views")