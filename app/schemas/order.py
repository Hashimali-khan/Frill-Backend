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


class CreateOrderResponse(BaseModel):
    order: OrderOut
    payment_metadata: dict



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