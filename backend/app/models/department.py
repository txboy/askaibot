from datetime import datetime

from sqlalchemy import Identity, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr
from ..database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    token_limit_daily: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
