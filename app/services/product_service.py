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
    result= await db.execute(_query().where(Product.slug == slug))
    return result.scalars().unique().one_or_none()
    

async def get_by_id (db: AsyncSession, product_id: UUID) -> Product | None:
    result = await db.execute(_query().where(Product.id== product_id))
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
