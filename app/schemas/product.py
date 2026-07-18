from sqlalchemy import label
from datetime import datetime

from pydantic import BaseModel, computed_field


class PrintArea(BaseModel):
    x:float
    y: float
    width: float
    height: float


class ProductViewIn(BaseModel):
    label: str
    image_url:str
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
    created_at: datetime | None = None     
    model_config = {"from_attributes": True}


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