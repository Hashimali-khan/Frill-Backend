from redis import retry
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.product import Product, ProductColor,ProductView
from app.schemas.product import ProductCreate,ProductUpdate

SORT_MAP= {
    "price-asc": Product.price.asc(),
    "price-desc": Product.price.desc(),
    "name_az": Product.name.asc(),
    "name_za": Product.name.desc()

}


_LIKE_ESCAPE_RE = re.compile(r"([%_\\])")

def _escape_like(s: str) -> str:
    return _LIKE_ESCAPE_RE.sub(r"\\\1", s)


def _query():
    return select(Product).options(
        selectinload(Product.colors).selectinload(Product.views)
    )

