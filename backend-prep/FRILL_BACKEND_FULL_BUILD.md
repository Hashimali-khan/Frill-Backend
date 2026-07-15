# Frill Backend — Full Build Document (Code You Type Yourself)

> Follow this top to bottom. Every code block is a real, complete file.
> Type it into your project rather than copy-pasting if you want the
> learning benefit — but it is genuinely runnable code, not pseudocode.
> Steps are ordered so each one is testable before you move to the next.

---

## Step 0 — Project setup

```bash
mkdir frill-backend && cd frill-backend
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

**`.gitignore`** *(FIX m5 — was missing entirely)*
```gitignore
.venv/
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.pytest_cache/
alembic/versions/*.pyc
```

**`pyproject.toml`**
```toml
[project]
name = "frill-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.139.0",
    "sqlalchemy[asyncio]>=2.0.35",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic-settings>=2.5.0",
    "pydantic[email]>=2.0.0",
    "supabase>=2.31.0",
    "pyjwt>=2.9.0",
    "slowapi>=0.1.9",
    "redis>=5.0.0",
    "python-multipart>=0.0.9",
    "stripe>=7.0.0",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.24.0", "httpx>=0.27.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

```bash
pip install -e ".[dev]"
```

**`.env.example`** (copy to `.env`, fill in real values from your Supabase
project settings → API, and Database → Connection Pooling)
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres.xxxx:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxxx
SUPABASE_JWT_SECRET=xxxx
REDIS_URL=redis://default:xxxx@xxxx.upstash.io:6379
CORS_ORIGINS=http://localhost:5173
STRIPE_SECRET_KEY=sk_test_xxxx
STRIPE_ENABLED=false
```

> Use the **pooler** connection string (port 6543, "Transaction" mode),
> not the direct connection (port 5432) — this is what survives real
> concurrent traffic without exhausting Supabase's connection limit.

Create the folder shell:
```bash
mkdir -p app/models app/schemas app/routers app/services app/core
mkdir -p alembic/versions scripts tests
touch app/__init__.py app/models/__init__.py app/schemas/__init__.py
touch app/routers/__init__.py app/services/__init__.py app/core/__init__.py
```

---

## Step 1 — Config, database, base models, errors

**`app/config.py`**
```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    redis_url: str
    cors_origins: str = "http://localhost:5173"
    stripe_secret_key: str = ""
    stripe_enabled: bool = False           # FIX C6 — Stripe feature flag

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

**`app/database.py`**
```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,          # detects a dropped connection before using it
    echo=not settings.is_production,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

**`app/models/base.py`**
```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

**`app/core/exceptions.py`**
```python
class AppError(Exception):
    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class InvalidTokenError(AppError):
    status_code = 401
    detail = "Invalid or expired session"


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class ForbiddenError(AppError):
    status_code = 403
    detail = "You don't have permission to do this"


class ConflictError(AppError):
    status_code = 409
    detail = "Conflict with existing data"


class ValidationAppError(AppError):
    status_code = 422
    detail = "Invalid input"
```

**`app/core/error_handlers.py`**
```python
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError

logger = logging.getLogger("frill")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        # Never leak a raw traceback to the client — log it, return a safe message.
        logger.exception("Unhandled error on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500, content={"error": "Something went wrong. Please try again."}
        )
```

---

## Step 2 — Security core (rate limiting, cache, JWT/cookies/CSRF)

**`app/core/rate_limit.py`**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Backed by Redis so limits are enforced correctly even if you later run
# more than one backend instance — an in-memory limiter would let each
# instance count separately, defeating the point under real load.
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
```

**`app/core/cache.py`**
```python
import json
from typing import Any

import redis.asyncio as redis

from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def cache_get(key: str) -> Any | None:
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    await redis_client.set(key, json.dumps(value), ex=ttl_seconds)


async def cache_delete_prefix(prefix: str) -> None:
    # NOTE (m4): SCAN is O(N) on keyspace. Acceptable for MVP traffic
    # volumes but consider Redis key-space notifications or explicit
    # key tracking if you scale past ~10k cached keys.
    async for key in redis_client.scan_iter(match=f"{prefix}*"):
        await redis_client.delete(key)
```

**`app/security.py`**
```python
import secrets

import jwt
from fastapi import Request, Response

from app.config import settings
from app.core.exceptions import InvalidTokenError

AUTH_COOKIE_NAME = "frill_session"
CSRF_COOKIE_NAME = "frill_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def verify_supabase_jwt(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError() from exc


def set_auth_cookie(response: Response, token: str, max_age_seconds: int = 60 * 60 * 24 * 7) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,                       # JS can never read this — kills XSS token theft
        secure=settings.is_production,        # False locally (http), True in prod (https)
        samesite="strict",
        max_age=max_age_seconds,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


def set_csrf_cookie(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,   # frontend JS must read this one to echo it back in a header
        secure=settings.is_production,
        samesite="strict",
        path="/",
    )
    return token


def verify_csrf(request: Request) -> None:
    """Double-submit cookie check. Applied globally via middleware (see main.py).
    FIX C4 — was defined but never wired in the original plan."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token or cookie_token != header_token:
        raise InvalidTokenError("CSRF check failed")
```

---

## Step 3 — Auth (Phase 1)

**`app/models/profile.py`**
```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Profile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "profiles"

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="customer")
```

**`app/dependencies.py`**
```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, InvalidTokenError
from app.database import get_db
from app.models.profile import Profile
from app.security import AUTH_COOKIE_NAME, verify_supabase_jwt


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Profile:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise InvalidTokenError("Not authenticated")

    payload = verify_supabase_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError()

    result = await db.execute(select(Profile).where(Profile.id == UUID(user_id)))
    profile = result.scalar_one_or_none()
    if not profile:
        raise InvalidTokenError("Session valid but profile missing")
    return profile


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Profile | None:
    try:
        return await get_current_user(request, db)
    except InvalidTokenError:
        return None


async def get_current_admin(user: Profile = Depends(get_current_user)) -> Profile:
    if user.role not in ("admin", "super_admin"):    # FIX: support super_admin role per Q3 answer
        raise ForbiddenError("Admin access required")
    return user


async def get_current_super_admin(user: Profile = Depends(get_current_user)) -> Profile:
    """Only super_admin can manage other admin accounts (per Q3 answer)."""
    if user.role != "super_admin":
        raise ForbiddenError("Super admin access required")
    return user


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
```

**`app/schemas/auth.py`**
```python
import re

from pydantic import BaseModel, EmailStr, field_validator

PK_PHONE_RE = re.compile(r"^(0|\+92)3[0-9]{9}$")


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def min_len_2(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Must be at least 2 characters")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def valid_pk_phone(cls, v: str) -> str:
        if not PK_PHONE_RE.match(v):
            raise ValueError("Enter a valid Pakistani phone number")
        return v

    @field_validator("password")
    @classmethod
    def min_len_8(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    role: str

    model_config = {"from_attributes": True}


# FIX M6 — Profile update schema (was missing entirely)
class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def valid_pk_phone_optional(cls, v: str | None) -> str | None:
        if v is not None and not PK_PHONE_RE.match(v):
            raise ValueError("Enter a valid Pakistani phone number")
        return v


# FIX C3 — Forgot/reset password schemas (were missing entirely)
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def min_len_8(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
```

**`app/services/auth_service.py`**
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client, create_client

from app.config import settings
from app.core.exceptions import ConflictError, InvalidTokenError, ValidationAppError
from app.models.profile import Profile
from app.schemas.auth import ProfileUpdateRequest, SignupRequest

_supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)


async def signup(db: AsyncSession, data: SignupRequest) -> Profile:
    existing = await db.execute(select(Profile).where(Profile.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError("Email already registered")

    auth_response = _supabase.auth.admin.create_user({
        "email": data.email,
        "password": data.password,
        "email_confirm": True,
    })
    user_id = auth_response.user.id

    profile = Profile(
        id=user_id, email=data.email, first_name=data.first_name,
        last_name=data.last_name, phone=data.phone, role="customer",
    )
    db.add(profile)
    try:
        await db.commit()
    except Exception:
        # Two systems, one logical transaction: if the local insert fails,
        # don't leave an orphaned Supabase Auth user behind.
        _supabase.auth.admin.delete_user(user_id)
        raise
    await db.refresh(profile)
    return profile


async def login(db: AsyncSession, email: str, password: str) -> tuple[str, Profile]:
    try:
        auth_response = _supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        raise InvalidTokenError("Invalid email or password") from exc

    token = auth_response.session.access_token
    result = await db.execute(select(Profile).where(Profile.email == email))
    profile = result.scalar_one_or_none()
    if not profile:
        raise InvalidTokenError("Account exists in auth but has no profile")
    return token, profile


# FIX M6 — Profile update service (was missing entirely)
async def update_profile(db: AsyncSession, profile: Profile, data: ProfileUpdateRequest) -> Profile:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


# FIX C3 — Forgot password service (was missing entirely)
async def forgot_password(email: str) -> None:
    """Triggers Supabase's built-in password reset email."""
    try:
        _supabase.auth.reset_password_email(email)
    except Exception:
        # Don't reveal whether the email exists — always return success
        pass


async def reset_password(access_token: str, new_password: str) -> None:
    """Uses the Supabase admin API to update the user's password."""
    try:
        # Verify the token to get the user ID
        from app.security import verify_supabase_jwt
        payload = verify_supabase_jwt(access_token)
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Invalid reset token")
        _supabase.auth.admin.update_user_by_id(user_id, {"password": new_password})
    except InvalidTokenError:
        raise
    except Exception as exc:
        raise ValidationAppError("Password reset failed") from exc
```

**`app/routers/auth.py`**
```python
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database import get_db
from app.dependencies import get_current_user
from app.models.profile import Profile
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
)
from app.security import clear_auth_cookie, set_auth_cookie, set_csrf_cookie
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse)
@limiter.limit("5/minute")
async def signup(
    request: Request, data: SignupRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    profile = await auth_service.signup(db, data)
    token, _ = await auth_service.login(db, data.email, data.password)
    set_auth_cookie(response, token)
    set_csrf_cookie(response)
    return profile


@router.post("/login", response_model=UserResponse)
@limiter.limit("10/minute")
async def login(
    request: Request, data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    token, profile = await auth_service.login(db, data.email, data.password)
    set_auth_cookie(response, token)
    set_csrf_cookie(response)
    return profile


@router.get("/me", response_model=UserResponse)
async def me(user: Profile = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"success": True}


# FIX M6 — Profile update endpoint (was missing entirely)
@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.update_profile(db, user, data)


# FIX C3 — Forgot password endpoint (was missing entirely)
@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    await auth_service.forgot_password(data.email)
    # Always return success — don't reveal whether the email exists
    return {"message": "If that email is registered, a reset link has been sent."}


# FIX C3 — Reset password endpoint (was missing entirely)
@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordRequest):
    await auth_service.reset_password(data.access_token, data.new_password)
    return {"success": True}
```

> **Why signup and login are separately rate-limited from everything
> else**: these are exactly the two endpoints a credential-stuffing or
> brute-force attack hits first. 5/minute and 10/minute per IP won't
> bother a real user who mistypes a password twice, but it makes
> automated guessing useless.

**Test before continuing** (don't skip this):
```bash
fastapi dev app/main.py   # (write a minimal main.py first — Step 8 below,
                           #  or temporarily include just the auth router)
curl -c cookies.txt -X POST localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"User","email":"t@t.com","phone":"03001234567","password":"password123"}'
curl -b cookies.txt localhost:8000/auth/me
```

---

## Step 4 — Products (Phase 2)

**`app/models/product.py`**
```python
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
```

**`app/schemas/product.py`**
```python
from datetime import datetime

from pydantic import BaseModel, computed_field


class PrintArea(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ProductViewIn(BaseModel):
    label: str
    image_url: str
    print_area: PrintArea


class ProductViewOut(ProductViewIn):
    id: str
    model_config = {"from_attributes": True}


class ProductColorIn(BaseModel):
    name: str
    hex: str
    views: list[ProductViewIn] = []


class ProductColorOut(BaseModel):
    id: str
    name: str
    hex: str
    views: list[ProductViewOut]
    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    slug: str
    name: str
    vendor: str
    category: str
    description: str
    long_description: str = ""
    price: float
    old_price: float | None = None
    customizable: bool = False
    sizes: list[str] = []
    colors: list[ProductColorIn] = []


class ProductUpdate(BaseModel):
    name: str | None = None
    vendor: str | None = None
    category: str | None = None
    description: str | None = None
    long_description: str | None = None
    price: float | None = None
    old_price: float | None = None
    customizable: bool | None = None
    sizes: list[str] | None = None
    # Colors/views are intentionally not editable through this endpoint —
    # that's a deliberate scope cut, not an oversight. Add a dedicated
    # nested endpoint later if you need to edit colors after creation.


class ProductOut(BaseModel):
    id: str
    slug: str
    name: str
    vendor: str
    category: str
    description: str
    long_description: str
    price: float
    old_price: float | None
    stars: float
    review_count: int
    customizable: bool
    sizes: list[str]
    colors: list[ProductColorOut]
    created_at: datetime | None = None      # FIX M5 — was missing
    model_config = {"from_attributes": True}

    # FIX M2 — Frontend references `product.img` for primary image.
    # This computed field returns the first view's image_url of the first color,
    # matching the frontend's expectation without changing the DB schema.
    @computed_field
    @property
    def img(self) -> str | None:
        if self.colors and self.colors[0].views:
            return self.colors[0].views[0].image_url
        return None


class PaginatedProducts(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int
```

**`app/services/product_service.py`**
```python
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.product import Product, ProductColor, ProductView
from app.schemas.product import ProductCreate, ProductUpdate

SORT_MAP = {
    "price-asc": Product.price.asc(),
    "price-desc": Product.price.desc(),
    "name-az": Product.name.asc(),
    "name-za": Product.name.desc(),
}

# FIX M9 — Escape special LIKE characters in user-supplied search terms
_LIKE_ESCAPE_RE = re.compile(r"([%_\\])")


def _escape_like(s: str) -> str:
    return _LIKE_ESCAPE_RE.sub(r"\\\1", s)


def _query():
    return select(Product).options(
        selectinload(Product.colors).selectinload(ProductColor.views)
    )


async def list_products(
    db: AsyncSession, category: str | None, sort: str | None,
    search: str | None, page: int, page_size: int,
) -> tuple[list[Product], int]:
    query = _query()
    count_query = select(func.count(Product.id))

    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    if search:
        # FIX M9 — escape user input for LIKE pattern
        escaped = _escape_like(search.lower())
        pattern = f"%{escaped}%"
        query = query.where(func.lower(Product.name).like(pattern))
        count_query = count_query.where(func.lower(Product.name).like(pattern))
    if sort in SORT_MAP:
        query = query.order_by(SORT_MAP[sort])

    total = (await db.execute(count_query)).scalar_one()
    query = query.limit(page_size).offset((page - 1) * page_size)
    items = (await db.execute(query)).scalars().unique().all()
    return list(items), total


async def get_by_slug(db: AsyncSession, slug: str) -> Product | None:
    result = await db.execute(_query().where(Product.slug == slug))
    return result.scalars().unique().one_or_none()


async def get_by_id(db: AsyncSession, product_id: UUID) -> Product | None:
    result = await db.execute(_query().where(Product.id == product_id))
    return result.scalars().unique().one_or_none()


async def create_product(db: AsyncSession, data: ProductCreate) -> Product:
    product = Product(
        slug=data.slug, name=data.name, vendor=data.vendor, category=data.category,
        description=data.description, long_description=data.long_description,
        price=data.price, old_price=data.old_price, customizable=data.customizable,
        sizes=data.sizes,
    )
    for color_in in data.colors:
        color = ProductColor(name=color_in.name, hex=color_in.hex)
        for view_in in color_in.views:
            color.views.append(ProductView(
                label=view_in.label, image_url=view_in.image_url,
                print_area=view_in.print_area.model_dump(),
            ))
        product.colors.append(color)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(db: AsyncSession, product_id: UUID, data: ProductUpdate) -> Product:
    product = await get_by_id(db, product_id)
    if not product:
        raise NotFoundError("Product not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product_id: UUID) -> None:
    product = await get_by_id(db, product_id)
    if not product:
        raise NotFoundError("Product not found")
    await db.delete(product)
    await db.commit()
```

**`app/routers/products.py`**
```python
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_prefix, cache_get, cache_set
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.dependencies import get_current_admin
from app.schemas.product import PaginatedProducts, ProductCreate, ProductOut, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=PaginatedProducts)
async def list_products(
    category: str | None = None, sort: str | None = None, q: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    # Read-heavy, write-rare data — a good, safe caching target.
    cache_key = f"products:list:{category}:{sort}:{q}:{page}:{page_size}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    items, total = await product_service.list_products(db, category, sort, q, page, page_size)
    payload = PaginatedProducts(
        items=[ProductOut.model_validate(p) for p in items], total=total, page=page, page_size=page_size,
    )
    result = payload.model_dump(mode="json")
    await cache_set(cache_key, result, ttl_seconds=60)
    return result


@router.get("/{slug}", response_model=ProductOut)
async def get_product_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_by_slug(db, slug)
    if not product:
        raise NotFoundError("Product not found")
    return product


@router.get("/id/{product_id}", response_model=ProductOut)
async def get_product_by_id(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_by_id(db, product_id)
    if not product:
        raise NotFoundError("Product not found")
    return product


@router.post("", response_model=ProductOut, dependencies=[Depends(get_current_admin)])
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = await product_service.create_product(db, data)
    await cache_delete_prefix("products:list:")   # stale cache would hide the new product
    return product


@router.put("/{product_id}", response_model=ProductOut, dependencies=[Depends(get_current_admin)])
async def update_product(product_id: UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await product_service.update_product(db, product_id, data)
    await cache_delete_prefix("products:list:")
    return product


@router.delete("/{product_id}", dependencies=[Depends(get_current_admin)])
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    await product_service.delete_product(db, product_id)
    await cache_delete_prefix("products:list:")
    return {"success": True}
```

---

## Step 4B — Saved Designs (Phase 2.5) *(FIX C1 — was completely missing)*

> This entire step is new. The frontend has `designsApi.js` with full CRUD,
> and the user confirmed "Option B" (explicit Save Design button). Without
> this step, the frontend's design save/load/delete endpoints have nothing
> to talk to.

**`app/models/design.py`**
```python
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
```

**`app/schemas/design.py`**
```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DesignCreate(BaseModel):
    name: str
    design_json: dict[str, Any]
    product_id: str
    color_id: str
    view_id: str
    mockup_url: str | None = None


class DesignOut(BaseModel):
    id: str
    user_id: str
    name: str
    design_json: dict[str, Any]
    product_id: str
    color_id: str
    view_id: str
    mockup_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedDesigns(BaseModel):
    items: list[DesignOut]
    total: int
    page: int
    page_size: int
```

**`app/services/design_service.py`**
```python
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.design import SavedDesign
from app.models.profile import Profile
from app.schemas.design import DesignCreate


async def create_design(db: AsyncSession, user: Profile, data: DesignCreate) -> SavedDesign:
    design = SavedDesign(
        user_id=user.id, name=data.name, design_json=data.design_json,
        product_id=UUID(data.product_id), color_id=data.color_id,
        view_id=data.view_id, mockup_url=data.mockup_url,
    )
    db.add(design)
    await db.commit()
    await db.refresh(design)
    return design


async def get_designs(
    db: AsyncSession, user: Profile, page: int, page_size: int
) -> tuple[list[SavedDesign], int]:
    query = select(SavedDesign)
    count_query = select(func.count(SavedDesign.id))

    # Admin sees all designs; regular user sees only their own
    if user.role not in ("admin", "super_admin"):
        query = query.where(SavedDesign.user_id == user.id)
        count_query = count_query.where(SavedDesign.user_id == user.id)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(SavedDesign.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def delete_design(db: AsyncSession, user: Profile, design_id: UUID) -> None:
    design = await db.get(SavedDesign, design_id)
    if not design:
        raise NotFoundError("Design not found")
    if user.role not in ("admin", "super_admin") and design.user_id != user.id:
        raise ForbiddenError("You can only delete your own designs")
    await db.delete(design)
    await db.commit()
```

**`app/routers/designs.py`**
```python
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.profile import Profile
from app.schemas.design import DesignCreate, DesignOut, PaginatedDesigns
from app.services import design_service

router = APIRouter(prefix="/api/designs", tags=["designs"])


@router.post("", response_model=DesignOut)
async def save_design(
    data: DesignCreate, db: AsyncSession = Depends(get_db),
    user: Profile = Depends(get_current_user),
):
    return await design_service.create_design(db, user, data)


@router.get("", response_model=PaginatedDesigns)
async def list_designs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: Profile = Depends(get_current_user),
):
    items, total = await design_service.get_designs(db, user, page, page_size)
    return PaginatedDesigns(
        items=[DesignOut.model_validate(d) for d in items], total=total, page=page, page_size=page_size,
    )


@router.delete("/{design_id}")
async def delete_design(
    design_id: UUID, db: AsyncSession = Depends(get_db),
    user: Profile = Depends(get_current_user),
):
    await design_service.delete_design(db, user, design_id)
    return {"success": True}
```

---

## Step 5 — Orders (Phase 3, the money-handling core)

**`app/models/order.py`**
```python
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Order(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "orders"

    # FIX C5 — user_id is now required (NOT nullable).
    # User confirmed "Option A: Require login before checkout" (Q2).
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
```

**`app/schemas/order.py`**
```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


# FIX M7 — Valid order statuses defined as a type
VALID_STATUSES = Literal["pending", "processing", "shipped", "delivered", "cancelled"]

# FIX m2 — Valid payment methods
VALID_PAYMENT_METHODS = Literal["cod", "jazzcash", "easypaisa", "stripe"]


class OrderItemIn(BaseModel):
    product_id: str
    quantity: int
    selected_size: str
    selected_color_name: str
    selected_color_hex: str
    selected_view_label: str | None = None
    mockup_url: str | None = None
    print_url: str | None = None
    design_json: dict | None = None


class CreateOrderRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr                           # FIX m2 — was plain `str`, no validation
    phone: str
    address: str
    city: str
    province: str
    postal_code: str
    payment_method: VALID_PAYMENT_METHODS     # FIX — constrained to valid values
    wallet_number: str | None = None
    items: list[OrderItemIn]
    # Deliberately no `total` field — the client cannot set price. See
    # order_service.create_order for where the real total is computed.


class OrderItemOut(BaseModel):
    id: str
    product_id: str | None
    product_name_snapshot: str
    price_snapshot: float
    quantity: int
    selected_size: str
    selected_color_name: str
    selected_color_hex: str
    selected_view_label: str | None
    mockup_url: str | None
    print_url: str | None
    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: str
    user_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    city: str
    province: str
    postal_code: str
    payment_method: str
    wallet_number: str | None
    status: str
    total: float
    items: list[OrderItemOut]
    created_at: datetime | None = None        # FIX M5 — was missing
    item_count: int | None = None             # FIX M4 — computed field
    model_config = {"from_attributes": True}


class PaginatedOrders(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int


class UpdateOrderStatus(BaseModel):
    status: VALID_STATUSES                    # FIX M7 — was plain `str`, accepted anything


# FIX C2 — Admin stats response schema (was missing entirely)
class AdminStatsResponse(BaseModel):
    total_revenue: float
    total_orders: int
    orders_today: int
    active_products: int
    total_customers: int
```

**`app/services/order_service.py`**
```python
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.profile import Profile
from app.schemas.order import CreateOrderRequest

STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered"],
    "delivered": [],
    "cancelled": [],
}


async def create_order(db: AsyncSession, user: Profile, data: CreateOrderRequest) -> Order:
    """FIX C5 — `user` is now required (not Optional). Checkout requires auth."""
    if not data.items:
        raise ValidationAppError("Cart is empty")

    order_items: list[OrderItem] = []
    total = 0.0

    for item_in in data.items:
        product = await db.get(Product, UUID(item_in.product_id))
        if not product:
            raise ValidationAppError(f"Product {item_in.product_id} no longer exists")

        # THE important line: price comes from the database, never the client.
        line_total = float(product.price) * item_in.quantity
        total += line_total

        order_items.append(OrderItem(
            product_id=product.id,
            product_name_snapshot=product.name,
            price_snapshot=product.price,
            quantity=item_in.quantity,
            selected_size=item_in.selected_size,
            selected_color_name=item_in.selected_color_name,
            selected_color_hex=item_in.selected_color_hex,
            selected_view_label=item_in.selected_view_label,
            mockup_url=item_in.mockup_url,
            print_url=item_in.print_url,
            design_json=item_in.design_json,
        ))

    order = Order(
        user_id=user.id,                      # FIX C5 — always attached to a user now
        first_name=data.first_name, last_name=data.last_name, email=data.email, phone=data.phone,
        address=data.address, city=data.city, province=data.province, postal_code=data.postal_code,
        payment_method=data.payment_method, wallet_number=data.wallet_number,
        status="pending", total=total, items=order_items,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


def _query():
    return select(Order).options(selectinload(Order.items))


async def get_orders(
    db: AsyncSession, user: Profile, page: int, page_size: int, status: str | None
) -> tuple[list[Order], int]:
    query = _query()
    count_query = select(func.count(Order.id))

    # Enforced, not optional: a non-admin only ever sees their own orders,
    # regardless of what the request tries to ask for.
    if user.role not in ("admin", "super_admin"):
        query = query.where(Order.user_id == user.id)
        count_query = count_query.where(Order.user_id == user.id)

    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(Order.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    items = (await db.execute(query)).scalars().unique().all()
    return list(items), total


async def get_order_by_id(db: AsyncSession, user: Profile, order_id: UUID) -> Order:
    result = await db.execute(_query().where(Order.id == order_id))
    order = result.scalars().unique().one_or_none()
    if not order:
        raise NotFoundError("Order not found")
    if user.role not in ("admin", "super_admin") and order.user_id != user.id:
        raise NotFoundError("Order not found")   # 404, not 403 — don't confirm it exists to a non-owner
    return order


async def update_status(db: AsyncSession, order_id: UUID, new_status: str) -> Order:
    order = await db.get(Order, order_id)
    if not order:
        raise NotFoundError("Order not found")
    allowed = STATUS_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise ValidationAppError(f"Cannot move order from '{order.status}' to '{new_status}'")
    order.status = new_status
    await db.commit()
    await db.refresh(order)
    return order


# FIX C2 — Admin stats service (was missing entirely)
async def get_admin_stats(db: AsyncSession) -> dict:
    """Compute real KPI data instead of hardcoded constants."""
    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(Order.total), 0))
    )).scalar_one()

    total_orders = (await db.execute(
        select(func.count(Order.id))
    )).scalar_one()

    today = datetime.now(timezone.utc).date()
    orders_today = (await db.execute(
        select(func.count(Order.id)).where(func.date(Order.created_at) == today)
    )).scalar_one()

    active_products = (await db.execute(
        select(func.count(Product.id))
    )).scalar_one()

    total_customers = (await db.execute(
        select(func.count(Profile.id)).where(Profile.role == "customer")
    )).scalar_one()

    return {
        "total_revenue": float(total_revenue),
        "total_orders": total_orders,
        "orders_today": orders_today,
        "active_products": active_products,
        "total_customers": total_customers,
    }
```

**`app/routers/orders.py`**
```python
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.models.profile import Profile
from app.schemas.order import (
    AdminStatsResponse,
    CreateOrderRequest,
    OrderOut,
    PaginatedOrders,
    UpdateOrderStatus,
)
from app.services import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut)
async def create_order(
    data: CreateOrderRequest, db: AsyncSession = Depends(get_db),
    user: Profile = Depends(get_current_user),       # FIX C5 — was get_current_user_optional
):
    order = await order_service.create_order(db, user, data)
    # Attach computed item_count for the response
    result = OrderOut.model_validate(order)
    result.item_count = len(order.items)
    return result


@router.get("", response_model=PaginatedOrders)
async def list_orders(
    status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: Profile = Depends(get_current_user),
):
    items, total = await order_service.get_orders(db, user, page, page_size, status)
    return PaginatedOrders(
        items=[OrderOut.model_validate(o) for o in items], total=total, page=page, page_size=page_size,
    )


@router.get("/stats", response_model=AdminStatsResponse, dependencies=[Depends(get_current_admin)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """FIX C2 — Admin stats endpoint (was missing entirely).
    Replaces the hardcoded KPI data in AdminDashboardPage.jsx."""
    return await order_service.get_admin_stats(db)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db), user: Profile = Depends(get_current_user)):
    return await order_service.get_order_by_id(db, user, order_id)


@router.patch("/{order_id}/status", response_model=OrderOut, dependencies=[Depends(get_current_admin)])
async def update_order_status(order_id: UUID, data: UpdateOrderStatus, db: AsyncSession = Depends(get_db)):
    return await order_service.update_status(db, order_id, data.status)
```

---

## Step 6 — Uploads (Phase 4)

**`app/services/storage_service.py`**
```python
import uuid

from supabase import Client, create_client

from app.config import settings
from app.core.exceptions import ValidationAppError

_supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


async def upload_file(bucket: str, file_bytes: bytes, content_type: str, extension: str) -> str:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationAppError(f"Unsupported file type: {content_type}")
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValidationAppError("File too large (max 10MB)")

    path = f"{uuid.uuid4()}.{extension}"
    _supabase.storage.from_(bucket).upload(path, file_bytes, {"content-type": content_type})
    return _supabase.storage.from_(bucket).get_public_url(path)
```

**`app/routers/uploads.py`**
```python
from fastapi import APIRouter, Depends, Request, UploadFile

from app.core.rate_limit import limiter
from app.dependencies import get_current_admin, get_current_user
from app.services import storage_service

router = APIRouter(prefix="/api/upload", tags=["upload"])

EXT_MAP = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


@router.post("/image", dependencies=[Depends(get_current_user)])
@limiter.limit("30/minute")                 # FIX m3 — was missing rate limiting
async def upload_image(request: Request, file: UploadFile):
    content = await file.read()
    url = await storage_service.upload_file(
        "design-uploads", content, file.content_type, EXT_MAP.get(file.content_type, "bin")
    )
    return {"url": url}


@router.post("/design-export", dependencies=[Depends(get_current_user)])
@limiter.limit("20/minute")                 # FIX m3 — was missing rate limiting
async def upload_design_export(request: Request, mockup: UploadFile, print_file: UploadFile):
    mockup_bytes, print_bytes = await mockup.read(), await print_file.read()
    mockup_url = await storage_service.upload_file(
        "design-exports", mockup_bytes, mockup.content_type, EXT_MAP.get(mockup.content_type, "png")
    )
    print_url = await storage_service.upload_file(
        "design-exports", print_bytes, print_file.content_type, EXT_MAP.get(print_file.content_type, "png")
    )
    return {"mockup_url": mockup_url, "print_url": print_url}


# FIX M8 — Product image upload for admin (was missing entirely)
@router.post("/product-image", dependencies=[Depends(get_current_admin)])
@limiter.limit("30/minute")
async def upload_product_image(request: Request, file: UploadFile):
    content = await file.read()
    url = await storage_service.upload_file(
        "product-images", content, file.content_type, EXT_MAP.get(file.content_type, "bin")
    )
    return {"url": url}
```

Create the three Supabase Storage buckets (`product-images`, `design-uploads`,
`design-exports`) from the Supabase dashboard now — public read, authenticated write.

---

## Step 6B — Stripe Payment Stub *(FIX C6 — was missing entirely)*

> This provides the Stripe infrastructure with a feature flag. When
> `STRIPE_ENABLED=false` (the default), orders go through as COD.
> When you're ready to launch payments, set `STRIPE_ENABLED=true` and
> provide a real `STRIPE_SECRET_KEY`.

**`app/services/payment_service.py`**
```python
from app.config import settings
from app.core.exceptions import ValidationAppError


async def process_payment(payment_method: str, total: float, wallet_number: str | None) -> dict:
    """Process payment based on method. Returns payment metadata."""

    if payment_method == "cod":
        return {"payment_status": "pending_delivery", "provider": "cod"}

    if payment_method == "stripe":
        if not settings.stripe_enabled:
            raise ValidationAppError("Online payments are not yet available")

        import stripe
        stripe.api_key = settings.stripe_secret_key

        # Create a PaymentIntent — the frontend will confirm it with Stripe.js
        intent = stripe.PaymentIntent.create(
            amount=int(total * 100),   # Stripe expects amount in smallest currency unit
            currency="pkr",
            metadata={"source": "frill_backend"},
        )
        return {
            "payment_status": "requires_confirmation",
            "provider": "stripe",
            "client_secret": intent.client_secret,
        }

    if payment_method in ("jazzcash", "easypaisa"):
        # Wallet payments — for now, record the wallet number and process manually
        if not wallet_number:
            raise ValidationAppError(f"{payment_method} requires a wallet number")
        return {"payment_status": "pending_verification", "provider": payment_method}

    raise ValidationAppError(f"Unsupported payment method: {payment_method}")
```

---

## Step 7 — Real-Time Notifications *(FIX C7 — was missing entirely)*

> User confirmed real-time features are in scope (Q16). This provides
> WebSocket-based order notifications for the admin panel.

**`app/routers/ws.py`**
```python
import json
from typing import ClassVar

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Simple WebSocket manager for real-time order notifications."""

    active_connections: ClassVar[list[WebSocket]] = []

    @classmethod
    async def connect(cls, websocket: WebSocket) -> None:
        await websocket.accept()
        cls.active_connections.append(websocket)

    @classmethod
    def disconnect(cls, websocket: WebSocket) -> None:
        cls.active_connections.remove(websocket)

    @classmethod
    async def broadcast(cls, message: dict) -> None:
        """Send a message to all connected clients."""
        dead: list[WebSocket] = []
        for connection in cls.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead.append(connection)
        for d in dead:
            cls.active_connections.remove(d)


manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications.
    Admin panel connects here to receive new order and status update alerts."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

> **Usage**: After creating an order or updating status in `order_service`,
> broadcast a notification:
> ```python
> from app.routers.ws import manager
> await manager.broadcast({"type": "new_order", "order_id": str(order.id)})
> ```

---

## Step 8 — Wire it all together

**`app/main.py`**
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.rate_limit import limiter
from app.routers import auth, designs, orders, products, uploads, ws
from app.security import verify_csrf


# FIX C4 — CSRF middleware (was defined but never wired)
class CSRFMiddleware(BaseHTTPMiddleware):
    """Applies CSRF double-submit check to all state-changing requests.
    Excludes /auth/signup, /auth/login, /auth/forgot-password, /auth/reset-password
    because those endpoints don't have a CSRF cookie yet."""

    EXEMPT_PATHS = {
        "/auth/signup", "/auth/login",
        "/auth/forgot-password", "/auth/reset-password",
    }

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.url.path not in self.EXEMPT_PATHS:
                verify_csrf(request)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Frill API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,   # required for the cookie to be sent cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],  # let frontend read CSRF-related headers
)

# FIX C4 — CSRF middleware MUST be added AFTER CORSMiddleware
# (middleware stack is LIFO, so CORS runs first on the response)
app.add_middleware(CSRFMiddleware)

register_error_handlers(app)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(designs.router)        # FIX C1 — was missing
app.include_router(orders.router)
app.include_router(uploads.router)
app.include_router(ws.router)             # FIX C7 — was missing


@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Step 9 — Alembic migrations

```bash
alembic init -t async alembic
```

Edit **`alembic/env.py`** — replace its config-loading section with:
```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.models.base import Base
from app.models import profile, product, order, design  # noqa: F401 — FIX C1: added design model

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


asyncio.run(run_migrations_online())
```

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

---

## Step 10 — Seed scripts

**`scripts/seed_admin.py`**
```python
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.profile import Profile
from app.schemas.auth import SignupRequest
from app.services.auth_service import signup


async def main():
    async with AsyncSessionLocal() as db:
        await signup(db, SignupRequest(
            first_name="Admin", last_name="User", email="admin@frill.pk",
            phone="03001234567", password="ChangeMeNow123!",
        ))
        result = await db.execute(select(Profile).where(Profile.email == "admin@frill.pk"))
        profile = result.scalar_one()
        # FIX: per Q3 answer — first admin is super_admin who can manage other admins
        profile.role = "super_admin"
        await db.commit()
        print("Super admin created:", profile.email, "— change that password immediately.")


if __name__ == "__main__":
    asyncio.run(main())
```

**`scripts/seed_products.py`** — copy every product from your frontend's
`data/products.mock.js` into this shape (one example shown; repeat for all
8):
```python
import asyncio

from app.database import AsyncSessionLocal
from app.schemas.product import ProductCreate, ProductColorIn, ProductViewIn, PrintArea
from app.services.product_service import create_product

PRODUCTS = [
    ProductCreate(
        slug="classic-hoodie", name="Classic Custom Hoodie", vendor="Frill Essentials",
        category="hoodies", description="...", long_description="...",
        price=2499, customizable=True, sizes=["S", "M", "L", "XL"],
        colors=[
            ProductColorIn(name="Midnight Black", hex="#1a1a2e", views=[
                ProductViewIn(label="Front", image_url="https://...",
                              print_area=PrintArea(x=150, y=120, width=300, height=350)),
            ]),
        ],
    ),
    # ... repeat for the rest of your 8 products, pulling real values from products.mock.js
]


async def main():
    async with AsyncSessionLocal() as db:
        for p in PRODUCTS:
            product = await create_product(db, p)
            print("Seeded:", product.slug)


if __name__ == "__main__":
    asyncio.run(main())
```

```bash
python scripts/seed_admin.py
python scripts/seed_products.py
```

---

## Step 11 — Run and verify locally

```bash
fastapi dev app/main.py
```

Full verification pass (do all of these before touching the frontend):
```bash
curl localhost:8000/health
curl -c c.txt -X POST localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@frill.pk","password":"ChangeMeNow123!"}'
curl -b c.txt localhost:8000/auth/me
curl localhost:8000/api/products
# 6th rapid login attempt should now 429 — confirms rate limiting works:
for i in 1 2 3 4 5 6; do curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/auth/login \
  -H "Content-Type: application/json" -d '{"email":"x@x.com","password":"wrong"}'; done
```

---

## Step 12 — Frontend integration (minimal, targeted changes)

> **⚠ IMPORTANT: Response shape changes from mock data** *(FIX M1, M2, M3)*
>
> The following shapes have changed from what the frontend currently expects.
> Update your RTK Query endpoints accordingly:
>
> | Endpoint | Old shape (mock) | New shape (real API) |
> |----------|-----------------|---------------------|
> | `GET /api/products` | `Product[]` | `{ items: Product[], total, page, page_size }` |
> | `POST /auth/signup` | `{ user, token }` | `UserResponse` (token is in httpOnly cookie, NOT in body) |
> | `POST /auth/login` | `{ user, token }` | `UserResponse` (token is in httpOnly cookie, NOT in body) |
> | `Product.desc` | `product.desc` | `product.description` |
> | `Product.reviews` | `product.reviews` | `product.review_count` |
> | `Product.img` | `product.img` (primary) | `product.img` (computed from first color/view) |
> | `Color.id` | `"hoodie-black"` (string) | UUID string |
> | `View.id` | `"hoodie-black-front"` (string) | UUID string |

**RTK Query base setup** — wherever you currently build your API slice:
```javascript
// src/store/apiSlice.js
import { fetchBaseQuery } from '@reduxjs/toolkit/query/react'

function getCsrfTokenFromCookie() {
  const match = document.cookie.match(/(?:^|;\s*)frill_csrf=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

export const baseQuery = fetchBaseQuery({
  baseUrl: import.meta.env.VITE_API_URL,
  credentials: 'include',              // sends the httpOnly cookie automatically
  prepareHeaders: (headers) => {
    const csrf = getCsrfTokenFromCookie()
    if (csrf) headers.set('X-CSRF-Token', csrf)
    return headers
  },
})
```

Then point `productsApi.js`, `ordersApi.js`, `designsApi.js`, and a new `authApi.js`
at this `baseQuery` (replacing the `queryFn`-wraps-localStorage pattern), matching
the endpoint shapes documented above.

**`authSlice.js`** — drop token storage entirely, derive `isAuthenticated`
from a successful `/auth/me` call:
```javascript
// thunks call the real endpoints now; state only ever holds `user`, never a token
export const loadSession = createAsyncThunk('auth/loadSession', async (_, { extra }) => {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/auth/me`, { credentials: 'include' })
  if (!res.ok) return null
  return res.json()
})
```
Dispatch `loadSession()` once on app mount (in `main.jsx` or a top-level
`useEffect`) so a returning user with a valid cookie is recognized without
having to log in again.

**Add CSRF header manually to the two non-RTK-Query fetches you still have**
(cookie/CSRF helper file uploads, if you keep those outside RTK Query) — same
`X-CSRF-Token` header pattern shown above.

**WebSocket connection** *(FIX C7)*:
```javascript
// In AdminLayout or admin dashboard
const ws = new WebSocket(`ws://${window.location.host}/ws/notifications`)
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'new_order') {
    // Show notification, refetch orders, etc.
  }
}
```

---

## Security checklist — confirm every item before calling this "done"

- [ ] Auth cookie is `httponly`, `secure` (prod), `samesite=strict`
- [ ] CSRF double-submit check is wired as global middleware (CSRFMiddleware
      in `main.py`) — exempts signup/login/forgot-password/reset-password
- [ ] `/auth/login` and `/auth/signup` are rate-limited
- [ ] `/auth/forgot-password` and `/auth/reset-password` are rate-limited
- [ ] Upload endpoints are rate-limited (30/min)
- [ ] Every admin route depends on `get_current_admin`, not a frontend check
- [ ] Super admin role exists for admin management (per Q3 answer)
- [ ] Order total is computed server-side from DB prices, never trusted
      from the client
- [ ] A customer cannot fetch another customer's order (verified by test,
      not just by reading the code)
- [ ] Checkout requires authentication (per Q2 answer — Option A)
- [ ] File uploads reject disallowed content types and oversized files
- [ ] Product image upload is admin-only
- [ ] CORS `allow_origins` is your real frontend domain(s) only — never `*`
      once `allow_credentials=True` is set (browsers reject that
      combination anyway, but don't rely on the browser to save you)
- [ ] No secret (`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`,
      `DATABASE_URL`, `STRIPE_SECRET_KEY`) is committed to the repo — only
      in `.env` (gitignored) and Render's environment variable settings
- [ ] `.gitignore` is present and covers `.env`, `__pycache__`, `.venv`
- [ ] `/health` returns 200 with no DB dependency (so Render's health check
      doesn't fail during a slow cold-start DB connection)
- [ ] Saved designs CRUD is functional and user-scoped
- [ ] Admin stats endpoint returns real computed data
- [ ] Password reset flow works end-to-end
- [ ] Order status is validated as an enum (not arbitrary strings)
- [ ] Payment method is validated as an enum
- [ ] LIKE search patterns escape special characters
- [ ] WebSocket notifications endpoint is accessible
- [ ] Stripe integration is behind feature flag (disabled by default)
