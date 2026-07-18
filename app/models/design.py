import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class SavedDesign(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "saved_designs"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    design_json: Mapped[dict] = mapped_column(JSONB)     # serialized design from studioUtils.serializeDesign()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    color_id: Mapped[str] = mapped_column(String)         # frontend color reference
    view_id: Mapped[str] = mapped_column(String)           # frontend view reference
    mockup_url: Mapped[str | None] = mapped_column(String, nullable=True)

    