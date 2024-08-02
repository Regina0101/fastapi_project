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
async def read_users_me(current_user: User = Depends(auth.get_current_user)):
    return current_user

@router.patch("/upload-avatar/", response_model=dict)
async def upload_avatar(file: UploadFile = File(),session: AsyncSession = Depends(get_async_session),
                        current_user: User = Depends(auth.get_current_user)):
    try:
        result = cloudinary.uploader.upload(file.file, public_id=f"{current_user.email}", owerite=True, width=250, height=250)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e} uploading image")

    image_url = result.get("secure_url")
    if not image_url:
        raise HTTPException(status_code=500, detail="Could not retrieve image URL")

    current_user.avatar = image_url
    session.add(current_user)
    await session.commit()

    return {"avatar_url": image_url}
