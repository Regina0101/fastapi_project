from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.entity.models import Contact, User
from src.schemas.contact import ContactRead, ContactCreate
from src.database.db import get_async_session
from src.services.auth import auth

router = APIRouter(prefix='/contacts', tags=['contacts'])

@router.post("/", response_model=ContactRead)
async def create_contact(contact: ContactCreate, session: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(auth.get_current_user)):
    new_contact = Contact(**contact.dict(), user_id=current_user.id)
    session.add(new_contact)
    await session.commit()
    await session.refresh(new_contact)
    return new_contact

@router.get("/{contact_id}", response_model=ContactRead)
async def read_contact(contact_id: int, session: AsyncSession = Depends(get_async_session),
                       current_user: User = Depends(auth.get_current_user)):
    query = select(Contact).filter(Contact.id == contact_id)
    result = await session.execute(query)
    contact = result.scalars().first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    if contact.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to read this contact")

    return contact

@router.put("/{contact_id}", response_model=ContactRead)
async def update_contact(contact_id: int, contact: ContactCreate, session: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(auth.get_current_user)):
    query = select(Contact).filter(Contact.id == contact_id)
    result = await session.execute(query)
    existing_contact = result.scalars().first()
    if existing_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    if existing_contact.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this contact")

    for key, value in contact.dict().items():
        setattr(existing_contact, key, value)

    await session.commit()
    await session.refresh(existing_contact)
    return existing_contact

@router.delete("/{contact_id}", response_model=ContactRead)
async def delete_contact(contact_id: int, session: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(auth.get_current_user)):
    query = select(Contact).filter(Contact.id == contact_id)
    result = await session.execute(query)
    contact = result.scalars().first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    if contact.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this contact")

    await session.delete(contact)
    await session.commit()
    return contact