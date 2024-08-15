from pydantic import ConfigDict, EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_URL: str = "postgresql+asyncpg://postgres:12345678@localhost:5432/fast_db"
    SECRET_KEY: str = "123456789"
    ALGORITHM: str = "HS256"
    MAIL_USERNAME: EmailStr = "user@gmail.com"
    MAIL_PASSWORD: str = "543678"
    MAIL_FROM: str = "user@gmail.com"
    MAIL_PORT: int = 8000
    MAIL_SERVER: str = "server.mt.ua"
    REDIS_DOMAIN: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    CLD_NAME: str = "fast_db"
    CLD_API_KEY: int = 1234567
    CLD_API_SECRET: str = "secret"


    model_config = ConfigDict(extra="ignore", env_file = ".env",env_file_encoding = "utf-8") # noqa


config = Settings()

