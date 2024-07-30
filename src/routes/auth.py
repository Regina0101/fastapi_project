from fastapi import APIRouter, HTTPException, Depends, Security, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from libgravatar import Gravatar
from src.entity.models import User
from src.schemas.user import UserBase, UserResponse, Token
from src.database.db import get_async_session
from src.services.auth import auth

router = APIRouter(prefix='/auth', tags=['auth'])

get_refresh_token = HTTPBearer()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: UserBase, session: AsyncSession = Depends(get_async_session)):
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
    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_async_session)):
    query = select(User).filter(User.email == form_data.username)
    result = await session.execute(query)
    user = result.scalars().first()

    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = await auth.create_access_token(data={"sub": user.email})
    new_refresh_token = await auth.refresh_access_token(data={"sub": user.email})

    user.refresh_token = new_refresh_token
    await session.commit()
    await session.refresh(user)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@router.get('/refresh_token', response_model=Token)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Security(get_refresh_token), session: AsyncSession = Depends(get_async_session)):
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
