import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import fakeredis.aioredis

from main import app
from src.entity.models import Base, User
from src.database.db import get_async_session
from src.services.auth import auth

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./my_test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = async_sessionmaker(autocommit=False, expire_on_commit=False, autoflush=False, bind=engine)


@pytest_asyncio.fixture(scope="module")
def init_models_wrap():
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as session:
            # Test User
            hashed_password = auth.get_password_hash("12345678")
            current_user = User(user_name="deadpool", email="deadpool@example.com", password=hashed_password)
            print(current_user)
            print(hashed_password)
            session.add(current_user)
            await session.commit()
            print("Test user added")
    asyncio.run(init_models())

@pytest_asyncio.fixture(scope="function")
async def session(init_models_wrap):
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
def client(session):
    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception as err:
                print(err)
                await session.rollback()

    app.dependency_overrides[get_async_session] = override_get_db

    with patch('fastapi_limiter.depends.RateLimiter.__call__', return_value=lambda x: x):
        yield TestClient(app)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def redis_client_mock(monkeypatch):
    redis_mock = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr('src.services.auth.redis_client', redis_mock)
    yield redis_mock


@pytest_asyncio.fixture()
async def get_token():
    token = await auth.create_access_token(data={"sub": "deadpool@example.com"})
    return token