
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base,TimestampMixin,UUIDMixin

class Profile(Base,TimestampMixin,UUIDMixin):
    __tablename__ = "profiles"

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="customer")
    

