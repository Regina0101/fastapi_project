import unittest
from datetime import timedelta, datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from src.entity.models import User
from src.services.auth import Auth


class TestAuth(unittest.TestCase):

    def setUp(self):
        self.auth = Auth()
        self.user = User(id=1, user_name="John", password="password", email="test@gmail.com")

    def test_verify_password(self):
        hashed_password = self.auth.get_password_hash("password")
        self.assertTrue(self.auth.verify_password("password", hashed_password))
        self.assertFalse(self.auth.verify_password("wrongpassword", hashed_password))

    def test_get_password_hash(self):
        password = "password"
        hashed_password = self.auth.get_password_hash(password)
        self.assertNotEqual(hashed_password, password)
        self.assertTrue(self.auth.verify_password(password, hashed_password))


class TestAuthAsync(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.auth = Auth()
        self.user = User(id=1, user_name="John", password="password", email="test@gmail.com")

    async def test_create_access_token(self):
        data = {"sub": "test@gmail.com"}
        access_token = await self.auth.create_access_token(data, expires_delta=timedelta(minutes=15))
        self.assertIsNotNone(access_token)

    async def test_create_email_token(self):
        data = {"sub": "test@gmail.com"}
        email_token = await self.auth.create_email_token(data)
        self.assertIsNotNone(email_token)

    async def test_get_email_from_token(self):
        data = {"sub": "test@gmail.com"}
        email_token = await self.auth.create_email_token(data)
        email = await self.auth.get_email_from_token(email_token)
        self.assertEqual(email, "test@gmail.com")

    @patch('src.services.auth.Auth.get_current_user')
    async def test_get_current_user(self, mock_get_data):
        mock_get_data.return_value = self.user
        data = {"sub": "test@gmail.com"}
        expires_delta = timedelta(minutes=15)
        token = await self.auth.create_access_token(data, expires_delta)

        result = await self.auth.get_current_user(token)
        self.assertEqual(result.email, "test@gmail.com")
        self.assertEqual(result.user_name, "John")


if __name__ == '__main__':
    unittest.main()




