from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
import cloudinary
import cloudinary.uploader
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_async_session
from src.entity.models import User
from src.schemas.user import UserResponse
from src.services.auth import auth
from src.conf.config import config

cloudinary.config(
    cloud_name=config.CLD_NAME,
    api_key=config.CLD_API_KEY,
    api_secret=config.CLD_API_SECRET
)

router = APIRouter(prefix='/users', tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(auth.get_current_user)
) -> UserResponse:
    """
    Retrieves the currently authenticated user's profile information.

    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The profile information of the current user.
    :rtype: UserResponse
    """
    return current_user


@router.patch("/upload-avatar/", response_model=dict)
async def upload_avatar(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(auth.get_current_user)
) -> dict:
    """
    Uploads a new avatar image for the currently authenticated user and updates their profile.

    :param file: The image file to be uploaded.
    :type file: UploadFile
    :param session: The database session.
    :type session: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: A dictionary containing the URL of the uploaded avatar.
    :rtype: dict
    :raises HTTPException: If there is an error uploading the image or retrieving its URL.
    """
    try:
        result = cloudinary.uploader.upload(
            file.file,
            public_id=f"{current_user.email}",
            overwrite=True,
            width=250,
            height=250
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e} uploading image")

    image_url = result.get("secure_url")
    if not image_url:
        raise HTTPException(status_code=500, detail="Could not retrieve image URL")

    current_user.avatar = image_url
    session.add(current_user)
    await session.commit()

    return {"avatar_url": image_url}
