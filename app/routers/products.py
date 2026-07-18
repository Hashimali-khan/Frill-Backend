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


@router.get ("/{slug}", response_model=ProductOut)
async def get_product_by_slug(slug:str, db: AsyncSession = Depends (get_db)):
    product = await product_service.get_by_slug(db, slug)
    if not product:
        raise NotFoundError("Product not Found")
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

response_model=ProductOut, dependencies=[Depends(get_current_admin)])
async def update_product(product_id: UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await product_service.update_product(db, product_id, data)
    await cache_delete_prefix("products:list:")
    return product


@router.delete("/{product_id}", dependencies=[Depends(get_current_admin)])
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    await product_service.delete_product(db, product_id)
    await cache_delete_prefix("products:list:")
    return {"success": True}

