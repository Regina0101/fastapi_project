from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.entity.models import Contact, User
from src.schemas.contact import ContactRead, ContactCreate
from src.database.db import get_async_session
from src.services.auth import auth

router = APIRouter(prefix='/contacts', tags=['contacts'])


@router.post("/", response_model=ContactRead, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def create_contact(
    contact: ContactCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(auth.get_current_user)
) -> ContactRead:
    """
    Creates a new contact for the currently authenticated user.

    :param contact: The contact data to be created.
    :type contact: ContactCreate
    :param session: The database session.
    :type session: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The created contact.
    :rtype: ContactRead
    """
    new_contact = Contact(**contact.dict(), user_id=current_user.id)
    session.add(new_contact)
    await session.commit()
    await session.refresh(new_contact)
    return new_contact


@router.get("/{contact_id}", response_model=ContactRead, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def read_contact(
    contact_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(auth.get_current_user)
) -> ContactRead:
    """
    Retrieves a specific contact by its ID.

    :param contact_id: The ID of the contact to retrieve.
    :type contact_id: UUID
    :param session: The database session.
    :type session: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The contact with the specified ID.
    :rtype: ContactRead
    :raises HTTPException: If the contact is not found or the user is not authorized to view it.
    """
    query = select(Contact).filter(Contact.id == contact_id)
    result = await session.execute(query)
    contact = result.scalars().first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    if contact.user_id != current_user.id and current_user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Not authorized to read this contact")

    return contact


@router.put("/{contact_id}", response_model=ContactRead, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def update_contact(
    contact_id: UUID,
    contact: ContactCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(auth.get_current_user)
) -> ContactRead:
    """
    Updates an existing contact with new data.

    :param contact_id: The ID of the contact to update.
    :type contact_id: UUID
    :param contact: The updated contact data.
    :type contact: ContactCreate
    :param session: The database session.
    :type session: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The updated contact.
    :rtype: ContactRead
    :raises HTTPException: If the contact is not found or the user is not authorized to update it.
    """
    query = select(Contact).filter(Contact.id == contact_id)
    result = await session.execute(query)
    existing_contact = result.scalars().first()
    if existing_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    if existing_contact.user_id != current_user.id and current_user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Not authorized to update this contact")

    for key, value in contact.dict().items():
        setattr(existing_contact, key, value)

    await session.commit()
    await session.refresh(existing_contact)
    return existing_contact

@router.delete("/{contact_id}", response_model=ContactRead, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def delete_contact(
    contact_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(auth.get_current_user)
) -> ContactRead:
    """
    Deletes a specific contact by its ID.

    :param contact_id: The ID of the contact to delete.
    :type contact_id: UUID
    :param session: The database session.
    :type session: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The deleted contact.
    :rtype: ContactRead
    :raises HTTPException: If the contact is not found or the user is not authorized to delete it.
    """
    query = select(Contact).filter(Contact.id == contact_id)
    result = await session.execute(query)
    contact = result.scalars().first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    if contact.user_id != current_user.id and current_user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Not authorized to delete this contact")

    await session.delete(contact)
    await session.commit()
    return contact
