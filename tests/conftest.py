import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.main import app
from app.models.base import Base
from app.models.profile import Profile

# In-memory SQLite engine for tests
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine, class_=AsyncSession)



@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables in the in-memory SQLite database before tests run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis cache functions."""
    with patch("app.core.cache.redis_client", new_callable=AsyncMock) as mock_redis_client:
        mock_redis_client.get.return_value = None
        # Make scan_iter return an async generator
        async def mock_scan_iter(*args, **kwargs):
            yield "test_key"
        mock_redis_client.scan_iter = mock_scan_iter
        yield mock_redis_client

@pytest_asyncio.fixture
async def db():
    """Yield a database session for a single test."""
    async with TestingSessionLocal() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()

@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """Test client with database override."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    
    # Bypass CSRF checks in tests by sending valid dummy tokens
    from app.security import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
    cookies = {CSRF_COOKIE_NAME: "test-csrf-token"}
    headers = {CSRF_HEADER_NAME: "test-csrf-token"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies, headers=headers) as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def mock_user(db: AsyncSession):
    """Create a mock regular user in the database."""
    user = Profile(
        id=uuid4(),
        email="testuser@example.com",
        first_name="Test",
        last_name="User",
        phone="03001234567",
        role="customer"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest_asyncio.fixture
async def mock_admin(db: AsyncSession):
    """Create a mock admin user in the database."""
    admin = Profile(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone="03001234568",
        role="admin"
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin

@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, mock_user: Profile):
    """Client authenticated as a regular user."""
    async def override_get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, mock_admin: Profile):
    """Client authenticated as an admin."""
    async def override_get_current_admin():
        return mock_admin
    async def override_get_current_user():
        return mock_admin
    app.dependency_overrides[get_current_admin] = override_get_current_admin
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_admin, None)
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture(autouse=True)
def mock_supabase():
    """Mock Supabase client for all tests to prevent real network calls."""
    mock_client = MagicMock()
    mock_client.auth.sign_in_with_password = MagicMock()
    mock_client.auth.sign_up = MagicMock()
    
    with patch("app.services.auth_service._supabase", mock_client), \
         patch("app.services.storage_service._supabase", mock_client):
        yield mock_client
