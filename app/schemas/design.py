from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DesignCreate(BaseModel):
    name: str
    design_json: dict[str, Any]
    product_id: str
    color_id: str
    view_id: str
    mockup_url: str | None = None


class DesignOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    design_json: dict[str, Any]
    product_id: UUID
    color_id: str
    view_id: str
    mockup_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class DesignStatusUpdate(BaseModel):
    status: str


class PaginatedDesigns(BaseModel):
    items: list[DesignOut]
    total: int
    page: int
    page_size: int