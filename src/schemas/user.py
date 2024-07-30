from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    user_name: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str


class UserInDB(UserBase):
    hashed_password: str


class UserResponse(BaseModel):
    id: int
    user_name: str
    email: EmailStr
    avatar: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
