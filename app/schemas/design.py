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