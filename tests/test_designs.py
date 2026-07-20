import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.fixture
async def mock_design(db, mock_user):
    from app.models.design import SavedDesign
    design = SavedDesign(
        id=uuid4(),
        user_id=mock_user.id,
        name="Test Design",
        design_json={"test": "data"},
        product_id=uuid4(),
        color_id="black",
        view_id="front",
        status="pending"
    )
    db.add(design)
    await db.commit()
    await db.refresh(design)
    return design

@pytest.mark.asyncio
async def test_create_design(auth_client: AsyncClient):
    response = await auth_client.post("/api/designs", json={
        "name": "My Custom Design",
        "design_json": {"elements": []},
        "product_id": str(uuid4()),
        "color_id": "white",
        "view_id": "back",
        "mockup_url": "http://example.com/mockup.png"
    })
    assert response.status_code == 200
    assert response.json()["name"] == "My Custom Design"
    assert response.json()["status"] == "pending"

@pytest.mark.asyncio
async def test_list_designs(auth_client: AsyncClient, mock_design):
    response = await auth_client.get("/api/designs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(d["id"] == str(mock_design.id) for d in data["items"])

@pytest.mark.asyncio
async def test_update_design_status_forbidden(auth_client: AsyncClient, mock_design):
    response = await auth_client.patch(f"/api/designs/{mock_design.id}/status", json={
        "status": "approved"
    })
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_update_design_status_admin(admin_client: AsyncClient, mock_design):
    response = await admin_client.patch(f"/api/designs/{mock_design.id}/status", json={
        "status": "approved"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

@pytest.mark.asyncio
async def test_delete_design(auth_client: AsyncClient, mock_design):
    response = await auth_client.delete(f"/api/designs/{mock_design.id}")
    assert response.status_code == 200
    
    response2 = await auth_client.get("/api/designs")
    assert not any(d["id"] == str(mock_design.id) for d in response2.json()["items"])
