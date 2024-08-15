import unittest
from unittest.mock import patch, AsyncMock
from src.services.email import send_email

class TestSendEmail(unittest.IsolatedAsyncioTestCase):
    @patch('src.services.email.MessageSchema')
    @patch('src.services.email.FastMail')
    async def test_send_email_arguments(self, MockFastMail, MockMessageSchema):
        email = "test@gmail.com"
        username = "user"
        host = "http://test.com"

        MockMessageSchema.return_value = AsyncMock()
        MockFastMail.return_value = AsyncMock()

        try:
            await send_email(email, username, host)
        except Exception as e:
            self.assertRaises(msg=f"send_email raised Exception unexpectedly: {e}")

        self.assertTrue(True, "send_email completed without raising an exception")

if __name__ == '__main__':
    unittest.main()