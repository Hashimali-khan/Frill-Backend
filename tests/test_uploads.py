import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_upload_image_unauthenticated(client: AsyncClient):
    response = await client.post("/api/upload/image")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_upload_image_valid(auth_client: AsyncClient, mock_supabase):
    # Mock supabase upload
    mock_supabase.storage.from_.return_value.get_public_url.return_value = "http://example.com/image.png"
    
    # Create a dummy image file
    file_content = b"fake image content"
    files = {"file": ("test.png", file_content, "image/png")}
    
    response = await auth_client.post("/api/upload/image", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert data["url"] == "http://example.com/image.png"

@pytest.mark.asyncio
async def test_upload_image_invalid_type(auth_client: AsyncClient):
    file_content = b"fake text content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    
    response = await auth_client.post("/api/upload/image", files=files)
    assert response.status_code in (400, 422)
    data = response.json()
    assert "detail" in data or "error" in data

@pytest.mark.asyncio
async def test_upload_design_export(auth_client: AsyncClient, mock_supabase):
    mock_supabase.storage.from_.return_value.get_public_url.return_value = "http://example.com/design.png"
    
    file_content = b"fake design content"
    files = {
        "mockup": ("mockup.png", file_content, "image/png"),
        "print_file": ("print.png", file_content, "image/png")
    }
    
    response = await auth_client.post("/api/upload/design-export", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "mockup_url" in data
    assert "print_url" in data

@pytest.mark.asyncio
async def test_upload_product_image_admin(admin_client: AsyncClient, mock_supabase):
    mock_supabase.storage.from_.return_value.get_public_url.return_value = "http://example.com/product.png"
    
    file_content = b"fake image"
    files = {"file": ("product.png", file_content, "image/png")}
    
    response = await admin_client.post("/api/upload/product-image", files=files)
    assert response.status_code == 200
    assert "url" in response.json()

@pytest.mark.asyncio
async def test_upload_product_image_forbidden(auth_client: AsyncClient):
    file_content = b"fake image"
    files = {"file": ("product.png", file_content, "image/png")}
    
    # Customer trying to upload product image
    response = await auth_client.post("/api/upload/product-image", files=files)
    assert response.status_code == 403
