from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String, index=True)
    last_name: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String, index=True)
    birthday: Mapped[Date] = mapped_column(Date)
    additional_info: Mapped[str | None] = mapped_column(String, nullable=True)