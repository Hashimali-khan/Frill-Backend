from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.profile import Profile
from app.routers.ws import manager
from app.schemas.order import CreateOrderRequest
from app.services import payment_service

STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered"],
    "delivered": [],
    "cancelled": [],
}


async def create_order(db: AsyncSession, user: Profile, data: CreateOrderRequest) -> tuple[Order, dict]:
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

    await manager.broadcast({"type": "new_order", "order_id": str(order.id)})

    payment_meta = await payment_service.process_payment(data.payment_method, total, data.wallet_number)

    return order, payment_meta


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
    await manager.broadcast({"type": "status_update", "order_id": str(order.id), "status": new_status})
    return order


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