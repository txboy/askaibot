from datetime import datetime

from sqlalchemy import Identity, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr
from ..database import Base


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserGroupMember(Base):
    __tablename__ = "user_group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)


class GroupGrant(Base):
    __tablename__ = "group_grants"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, index=True)
    resource_type: Mapped[str] = mapped_column(
        OrEmptyStr(255), default="", nullable=True
    )  # endpoint / knowledge_base / mcp / search / skill
    resource_id: Mapped[int] = mapped_column(Integer, default=0)
