import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient, mock_supabase):
    from uuid import uuid4
    class FakeUser:
        id = str(uuid4())
        email = "newuser@example.com"
    class FakeResponse:
        user = FakeUser()
    mock_supabase.auth.admin.create_user.return_value = FakeResponse()
    
    payload = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "first_name": "New",
        "last_name": "User",
        "phone": "03001234567"
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["email"] == payload["email"]
    assert data["first_name"] == payload["first_name"]
    
@pytest.mark.asyncio
async def test_signup_invalid_phone(client: AsyncClient):
    response = await client.post("/auth/signup", json={
        "email": "newuser@example.com",
        "password": "Password123!",
        "first_name": "New",
        "last_name": "User",
        "phone": "123" # invalid
    })
    assert response.status_code == 422
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_signup_short_password(client: AsyncClient):
    response = await client.post("/auth/signup", json={
        "email": "newuser@example.com",
        "password": "short", # length < 8
        "first_name": "New",
        "last_name": "User",
        "phone": "03001234567"
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, mock_supabase, mock_user):
    mock_res = MagicMock()
    mock_res.session.access_token = "mock_token"
    mock_res.session.refresh_token = "mock_refresh"
    mock_supabase.auth.sign_in_with_password = MagicMock(return_value=mock_res)
    
    response = await client.post("/auth/login", json={
        "email": "testuser@example.com",
        "password": "Password123!"
    })
    
    assert response.status_code == 200
    assert response.cookies.get("frill_session") == "mock_token"

@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_authenticated(auth_client: AsyncClient):
    response = await auth_client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "testuser@example.com"

@pytest.mark.asyncio
async def test_update_profile(auth_client: AsyncClient):
    response = await auth_client.put("/auth/profile", json={
        "first_name": "Updated",
        "last_name": "Name",
        "phone": "03009999999"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["phone"] == "03009999999"

@pytest.mark.asyncio
async def test_logout(auth_client: AsyncClient):
    response = await auth_client.post("/auth/logout")
    assert response.status_code == 200
    assert response.cookies.get("frill_session") in ["", None] # Cookie cleared
