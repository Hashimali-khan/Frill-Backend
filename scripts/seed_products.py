import asyncio

from app.database import AsyncSessionLocal
from app.schemas.product import ProductCreate, ProductColorIn, ProductViewIn, PrintArea
from app.services.product_service import create_product

import json

# Load from mocks.json
with open(r"c:\data\webdev\frill\mocks.json", "r", encoding="utf-8") as f:
    raw_products = json.load(f)

PRODUCTS = []
for p in raw_products:
    colors_in = []
    for c in p.get("colors", []):
        views_in = []
        for v in c.get("views", []):
            pa = v.get("printArea", {})
            views_in.append(ProductViewIn(
                label=v["label"],
                image_url=v["imageUrl"],
                print_area=PrintArea(
                    x=pa.get("x", 170),
                    y=pa.get("y", 180),
                    width=pa.get("width", 480),
                    height=pa.get("height", 520)
                ) if pa else None
            ))
        colors_in.append(ProductColorIn(
            name=c["name"],
            hex=c["hex"],
            views=views_in
        ))
    
    PRODUCTS.append(ProductCreate(
        slug=p["slug"],
        name=p["name"],
        vendor=p["vendor"],
        category=p["category"],
        description=p.get("desc", ""),
        long_description=p.get("longDesc", ""),
        price=p["price"],
        old_price=p.get("oldPrice"),
        stars=p.get("stars", 0.0),
        review_count=p.get("reviews", 0),
        customizable=p.get("customizable", False),
        sizes=p.get("sizes", []),
        colors=colors_in
    ))

async def main():
    async with AsyncSessionLocal() as db:
        for p in PRODUCTS:
            product = await create_product(db, p)
            print("Seeded:", product.slug)


if __name__ == "__main__":
    asyncio.run(main())