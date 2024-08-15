import logging
from fastapi import APIRouter, HTTPException, Depends, Security, status, BackgroundTasks, Request
import random
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from libgravatar import Gravatar
from src.entity.models import User
from src.schemas.user import UserBase, UserResponse, Token, RequestEmail, ResetPassword
from src.database.db import get_async_session
from src.services.auth import auth
from src.services.email import send_email
from src.services.auth import redis_client

router = APIRouter(prefix='/auth', tags=['auth'])

get_refresh_token = HTTPBearer()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: UserBase, request: Request, bt: BackgroundTasks, session: AsyncSession = Depends(get_async_session)):
    """
    Registers a new user in the system.

    :param body: The user data for registration.
    :type body: UserBase
    :param request: The request object, used to retrieve the base URL for the confirmation email.
    :type request: Request
    :param bt: Background tasks to handle sending confirmation emails asynchronously.
    :type bt: BackgroundTasks
    :param session: The database session used for querying and committing changes.
    :type session: AsyncSession
    :return: The newly created user, excluding the password.
    :rtype: UserResponse
    :raises HTTPException: If the email is already registered (status code 409).
    """
    query = select(User).filter(User.email == body.email)
    result = await session.execute(query)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    hashed_password = auth.get_password_hash(body.password)
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as err:
        print(err)
        avatar = None

    new_user = User(
        user_name=body.user_name,
        email=body.email,
        password=hashed_password,
        avatar=avatar
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    bt.add_task(send_email, new_user.email, new_user.user_name, str(request.base_url))
    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_async_session)):
    """
    Authenticates a user and returns an access token and refresh token.

    :param form_data: The user's login credentials.
    :type form_data: OAuth2PasswordRequestForm
    :param session: The database session used for querying.
    :type session: AsyncSession
    :return: A dictionary containing the access token, refresh token, and token type.
    :rtype: Token
    :raises HTTPException: If the credentials are invalid or the email is not confirmed (status code 401).
    """
    query = select(User).filter(User.email == form_data.username)
    result = await session.execute(query)
    user = result.scalars().first()

    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")

    access_token = await auth.create_access_token(data={"sub": user.email})
    new_refresh_token = await auth.refresh_access_token(data={"sub": user.email})

    user.refresh_token = new_refresh_token
    await session.commit()
    await session.refresh(user)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@router.get('/refresh_token', response_model=Token)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Security(get_refresh_token), session: AsyncSession = Depends(get_async_session)):
    """
    Refreshes the user's access token using the provided refresh token.

    :param credentials: The current refresh token provided in the request header.
    :type credentials: HTTPAuthorizationCredentials
    :param session: The database session used for querying and updating the user's tokens.
    :type session: AsyncSession
    :return: A dictionary containing the new access token, refresh token, and token type.
    :rtype: Token
    :raises HTTPException: If the refresh token is invalid or does not match the one stored in the database (status code 401).
    """
    refresh_token = credentials.credentials
    email = await auth.decode_refresh_token(refresh_token)

    query = select(User).filter(User.email == email)
    result = await session.execute(query)
    user = result.scalars().first()
    if user is None or user.refresh_token != refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await auth.create_access_token(data={"sub": email})
    new_refresh_token = await auth.refresh_access_token(data={"sub": email})
    user.refresh_token = new_refresh_token

    await session.commit()
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, session: AsyncSession = Depends(get_async_session)):
    """
    Confirms the user's email address using the provided verification token.

    :param token: The token sent to the user's email for verification.
    :type token: str
    :param session: The database session used for querying and updating the user's status.
    :type session: AsyncSession
    :return: A message indicating whether the email confirmation was successful.
    :rtype: dict
    :raises HTTPException: If the token is invalid or the user is not found (status code 400).
    """
    email = await auth.get_email_from_token(token)
    query = select(User).filter(User.email == email)
    result = await session.execute(query)
    user = result.scalars().first()

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")

    if user.confirmed:
        return {"message": "Your email is already confirmed"}

    user.confirmed = True
    await session.commit()
    return {"message": "Email confirmed successfully"}


@router.post('/request_email')
async def request_email(body: RequestEmail, background_tasks: BackgroundTasks, request: Request,
                        session: AsyncSession = Depends(get_async_session)):
    """
    Sends a confirmation email to the user if the email is not already confirmed.

    :param body: The email address to send the confirmation to.
    :type body: RequestEmail
    :param background_tasks: Background tasks to handle sending the email asynchronously.
    :type background_tasks: BackgroundTasks
    :param request: The request object used to retrieve the base URL for the confirmation email.
    :type request: Request
    :param session: The database session used for querying.
    :type session: AsyncSession
    :return: A message indicating that the confirmation email has been sent.
    :rtype: dict
    :raises HTTPException: If the user is not found (status code 404).
    """
    query = select(User).filter(User.email == body.email)
    result = await session.execute(query)
    user = result.scalars().first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.confirmed:
        return {"message": "Your email is already confirmed"}

    background_tasks.add_task(send_email, user.email, user.user_name, str(request.base_url))

    return {"message": "Check your email for confirmation."}


@router.post('/request_password_reset')
async def request_password_reset(body: RequestEmail, background_tasks: BackgroundTasks,
                                 session: AsyncSession = Depends(get_async_session)):
    """
    Sends a password reset code to the user's email if the account exists.

    :param body: The email address associated with the user account.
    :type body: RequestEmail
    :param background_tasks: Background tasks to handle sending the reset email asynchronously.
    :type background_tasks: BackgroundTasks
    :param session: The database session used for querying.
    :type session: AsyncSession
    :return: A message indicating that the password reset code has been sent.
    :rtype: dict
    """
    query = select(User).filter(User.email == body.email)
    result = await session.execute(query)
    user = result.scalars().first()

    if user:
        reset_code = str(random.randint(100000, 999999))
        await redis_client.setex(f"reset_code:{body.email}", 3600, reset_code)
        background_tasks.add_task(send_email, user.email, f"Your password reset code: {reset_code}", "Code")

    return {"message": "If an account with that email exists, a password reset code has been sent."}

@router.post('/reset_password')
async def reset_password(body: ResetPassword, session: AsyncSession = Depends(get_async_session)):
    """
    Resets the user's password using the provided reset code.

    :param body: The email address, reset code, and new password for the user.
    :type body: ResetPassword
    :param session: The database session used for querying and updating the user's password.
    :type session: AsyncSession
    :return: A message indicating that the password was successfully reset.
    :rtype: dict
    :raises HTTPException: If the reset code or email is invalid (status code 400).
    """
    stored_code = await redis_client.get(f"reset_code:{body.email}")
    if stored_code:
        stored_code = stored_code.decode('utf-8')
        if stored_code == body.reset_code:
            query = select(User).filter(User.email == body.email)
            result = await session.execute(query)
            user = result.scalars().first()

            if user:
                user.password = auth.get_password_hash(body.new_password)
                await session.commit()
                await redis_client.delete(f"reset_code:{body.email}")
                return {"message": "Password reset successfully"}

    raise HTTPException(status_code=400, detail="Invalid code or email")
