from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.entity.models import Contact
from src.schemas.contact import ContactRead, ContactCreate

from src.database.db import get_async_session

router = APIRouter(prefix='/contacts', tags=['contacts'])


async def get_contact(contact_id: int, session) -> Contact:
    query = select(Contact).filter(Contact.id == contact_id)
    result = await session.execute(query)
    contact = result.scalars().first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/", response_model=ContactRead)
async def create_contact(contact: ContactCreate, session=Depends(get_async_session)):
    new_contact = Contact(**contact.dict())
    session.add(new_contact)
    await session.commit()
    await session.refresh(new_contact)
    return new_contact


@router.get("/{contact_id}", response_model=ContactRead)
async def read_contact(contact_id: int, session= Depends(get_async_session)):
    return await get_contact(contact_id, session)


@router.put("/{contact_id}", response_model=ContactRead)
async def update_contact(contact_id: int, contact: ContactCreate, session: AsyncSession = Depends(get_async_session)):
    async with session.begin():
        query = select(Contact).filter(Contact.id == contact_id)
        result = await session.execute(query)
        existing_contact = result.scalars().first()
        if existing_contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")

        for key, value in contact.dict().items():
            setattr(existing_contact, key, value)

        await session.commit()
        await session.refresh(existing_contact)
    return existing_contact


@router.delete("/{contact_id}", response_model=ContactRead)
async def delete_contact(contact_id: int, session: AsyncSession = Depends(get_async_session)):
    async with session.begin():
        query = select(Contact).filter(Contact.id == contact_id)
        result = await session.execute(query)
        contact = result.scalars().first()
        if contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")

        await session.delete(contact)
        await session.commit()
    return contact