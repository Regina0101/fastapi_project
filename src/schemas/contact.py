from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import date
from src.schemas.user import UserResponse

class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthday: date
    additional_info: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactRead(ContactBase):
    id: UUID
    user: UserResponse | None

    class Config:
        from_attributes = True
