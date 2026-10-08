from sqlalchemy import Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(191), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(500), default="super")
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
