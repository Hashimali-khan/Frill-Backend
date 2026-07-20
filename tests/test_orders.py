import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.fixture
async def mock_product(db):
    from app.models.product import Product
    prod = Product(
        id=uuid4(), category="test-cat", name="Test Product", slug="test-prod",
        vendor="Test Vendor", description="Desc", price=1500.0
    )
    db.add(prod)
    await db.commit()
    await db.refresh(prod)
    return prod

@pytest.fixture
async def mock_order(db, mock_user):
    from app.models.order import Order
    order = Order(
        id=uuid4(), user_id=mock_user.id, first_name="Test", last_name="User",
        email="test@example.com", phone="03001234567", address="123 Street",
        city="Lahore", province="Punjab", postal_code="54000",
        payment_method="cod", status="pending", total=1500.0
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order

@pytest.mark.asyncio
async def test_create_order(auth_client: AsyncClient, mock_product):
    response = await auth_client.post("/api/orders", json={
        "first_name": "Test", "last_name": "User", "email": "test@example.com",
        "phone": "03001234567", "address": "123 Street", "city": "Lahore",
        "province": "Punjab", "postal_code": "54000", "payment_method": "cod",
        "items": [{
            "product_id": str(mock_product.id), "quantity": 2, "selected_size": "M",
            "selected_color_name": "Red", "selected_color_hex": "#FF0000"
        }]
    })
    assert response.status_code == 200
    data = response.json()
    assert "order" in data
    # Verify server-side total calculation: 2 * 1500.0 = 3000.0
    assert data["order"]["total"] == 3000.0

@pytest.mark.asyncio
async def test_create_order_empty_cart(auth_client: AsyncClient):
    response = await auth_client.post("/api/orders", json={
        "first_name": "Test", "last_name": "User", "email": "test@example.com",
        "phone": "03001234567", "address": "123 Street", "city": "Lahore",
        "province": "Punjab", "postal_code": "54000", "payment_method": "cod",
        "items": []
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_order_invalid_payment_method(auth_client: AsyncClient, mock_product):
    response = await auth_client.post("/api/orders", json={
        "first_name": "Test", "last_name": "User", "email": "test@example.com",
        "phone": "03001234567", "address": "123 Street", "city": "Lahore",
        "province": "Punjab", "postal_code": "54000", 
        "payment_method": "invalid_method", # Invalid
        "items": [{
            "product_id": str(mock_product.id), "quantity": 1, "selected_size": "M",
            "selected_color_name": "Red", "selected_color_hex": "#FF0000"
        }]
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_orders(auth_client: AsyncClient, mock_order):
    response = await auth_client.get("/api/orders")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(o["id"] == str(mock_order.id) for o in data["items"])

@pytest.mark.asyncio
async def test_get_order_by_id(auth_client: AsyncClient, mock_order):
    response = await auth_client.get(f"/api/orders/{mock_order.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_order.id)

@pytest.mark.asyncio
async def test_get_order_by_id_idor(auth_client: AsyncClient, db):
    # Create an order belonging to another user
    from app.models.order import Order
    other_order = Order(
        id=uuid4(), user_id=uuid4(), first_name="Other", last_name="User",
        email="other@example.com", phone="03001234567", address="123",
        city="LHR", province="Punjab", postal_code="54000",
        payment_method="cod", status="pending", total=100.0
    )
    db.add(other_order)
    await db.commit()
    await db.refresh(other_order)
    
    # Authenticated user tries to access other user's order
    response = await auth_client.get(f"/api/orders/{other_order.id}")
    assert response.status_code == 404 # Backend returns 404 for IDOR protection

@pytest.mark.asyncio
async def test_update_order_status_admin(admin_client: AsyncClient, mock_order):
    response = await admin_client.patch(f"/api/orders/{mock_order.id}/status", json={
        "status": "processing"
    })
    print("STATUS 422 DETAILS:", response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

@pytest.mark.asyncio
async def test_get_admin_stats(admin_client: AsyncClient, mock_order):
    response = await admin_client.get("/api/orders/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "total_orders" in data
