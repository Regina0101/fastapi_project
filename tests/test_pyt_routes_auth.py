import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from tests.conftest import TestingSessionLocal
from sqlalchemy import select

from src.entity.models import User

user_data = {"user_name": "spiderman","email": "spider@mail.com","password": "123456789"}

@pytest.mark.asyncio
async def test_signup(client: TestClient, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post("api/auth/signup", json=user_data)
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_login(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(select(User).where(User.email == user_data.get("email")))
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()

    response = client.post("api/auth/login",
                           data={"username": user_data.get("email"), "password": user_data.get("password")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data



@pytest.mark.asyncio
async def test_validation_error_login(client):
    response = client.post("api/auth/login", data={"password": user_data.get("password")})
    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data

