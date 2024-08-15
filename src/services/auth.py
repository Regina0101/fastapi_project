import pickle
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, timedelta, timezone
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_async_session
from src.entity.models import User
from src.conf.config import config

redis_client = Redis(host=config.REDIS_DOMAIN, port=config.REDIS_PORT, db=0, password=config.REDIS_PASSWORD)


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies a plain password against a hashed password.

        :param plain_password: The plain text password to verify.
        :type plain_password: str
        :param hashed_password: The hashed password to compare against.
        :type hashed_password: str
        :return: True if the passwords match, False otherwise.
        :rtype: bool
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Hashes a plain password.

        :param password: The plain text password to hash.
        :type password: str
        :return: The hashed password.
        :rtype: str
        """
        return self.pwd_context.hash(password)

    async def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Creates a new access token with an optional expiration delta.

        :param data: Data to encode in the token.
        :type data: dict
        :param expires_delta: Optional expiration time for the token.
        :type expires_delta: Optional[timedelta]
        :return: The encoded JWT access token.
        :rtype: str
        """
        to_encode = data.copy()
        if expires_delta is not None:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)

        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire, "scope": "access_token"})
        encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
        return encoded_jwt

    async def refresh_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Creates a new refresh token with an optional expiration delta.

        :param data: Data to encode in the token.
        :type data: dict
        :param expires_delta: Optional expiration time for the token.
        :type expires_delta: Optional[timedelta]
        :return: The encoded JWT refresh token.
        :rtype: str
        """
        to_encode = data.copy()
        if expires_delta is not None:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=7)

        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire, "scope": "refresh_token"})
        encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
        return encoded_jwt

    async def decode_refresh_token(self, refresh_token: str) -> str:
        """
        Decodes a refresh token and verifies its validity.

        :param refresh_token: The refresh token to decode.
        :type refresh_token: str
        :return: The email associated with the token.
        :rtype: str
        :raises HTTPException: If the token is invalid or has an incorrect scope.
        """
        try:
            payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            if payload['scope'] == 'refresh_token':
                return payload.get('sub')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid scope for token')
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials')

    async def get_current_user(self, token: str = Depends(oauth2_scheme),
                               db: AsyncSession = Depends(get_async_session)) -> User:
        """
        Retrieves the current user based on the provided token.

        :param token: The JWT token to decode and verify.
        :type token: str
        :param db: The database session.
        :type db: AsyncSession
        :return: The User object associated with the token.
        :rtype: User
        :raises HTTPException: If credentials are invalid or the user is not found.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            email = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        cached_user = await redis_client.get(email)

        if cached_user:
            user = pickle.loads(cached_user)
        else:
            query = select(User).filter(User.email == email)
            result = await db.execute(query)
            user = result.scalars().first()
            if user:
                await redis_client.set(email, pickle.dumps(user), ex=60*60)

        if user is None:
            raise credentials_exception

        return user

    async def create_email_token(self, data: dict) -> str:
        """
        Creates a token for email verification.

        :param data: Data to encode in the token.
        :type data: dict
        :return: The encoded JWT email verification token.
        :rtype: str
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=1)
        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire})
        token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
        return token

    async def get_email_from_token(self, token: str) -> str:
        """
        Extracts the email address from an email verification token.

        :param token: The email verification token to decode.
        :type token: str
        :return: The email address contained in the token.
        :rtype: str
        :raises HTTPException: If the token is invalid or cannot be decoded.
        """
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            email = payload["sub"]
            return email
        except JWTError as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Invalid token for email verification")


auth = Auth()
