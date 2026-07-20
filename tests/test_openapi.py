import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_openapi_json(client: AsyncClient):
    """Test that the OpenAPI spec generates successfully."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data

    # Ensure no sensitive fields like passwords are leaked in schemas
    schemas = data.get("components", {}).get("schemas", {})
    if "UserResponse" in schemas:
        props = schemas["UserResponse"].get("properties", {})
        assert "password" not in props
