from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.models.profile import Profile
from app.schemas.order import (
    AdminStatsResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    OrderOut,
    PaginatedOrders,
    UpdateOrderStatus,
)
from app.services import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=CreateOrderResponse)
async def create_order(
    data: CreateOrderRequest, db: AsyncSession = Depends(get_db),
    user: Profile = Depends(get_current_user),       # FIX C5 — was get_current_user_optional
):
    order, payment_meta = await order_service.create_order(db, user, data)
    # Attach computed item_count for the response
    result = OrderOut.model_validate(order)
    result.item_count = len(order.items)
    return CreateOrderResponse(order=result, payment_metadata=payment_meta)


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