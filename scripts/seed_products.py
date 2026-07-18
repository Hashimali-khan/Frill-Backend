import asyncio

from app.database import AsyncSessionLocal
from app.schemas.product import ProductCreate, ProductColorIn, ProductViewIn, PrintArea
from app.services.product_service import create_product

PRODUCTS = [
    ProductCreate(
        slug="classic-hoodie", name="Classic Custom Hoodie", vendor="Frill Essentials",
        category="hoodies", description="...", long_description="...",
        price=2499, customizable=True, sizes=["S", "M", "L", "XL"],
        colors=[
            ProductColorIn(name="Midnight Black", hex="#1a1a2e", views=[
                ProductViewIn(label="Front", image_url="https://...",
                              print_area=PrintArea(x=150, y=120, width=300, height=350)),
            ]),
        ],
    ),
    # ... repeat for the rest of your 8 products, pulling real values from products.mock.js
]


async def main():
    async with AsyncSessionLocal() as db:
        for p in PRODUCTS:
            product = await create_product(db, p)
            print("Seeded:", product.slug)


if __name__ == "__main__":
    asyncio.run(main())