from datetime import datetime

from sqlalchemy import Identity, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr
from ..database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    bot_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), default="新对话")
    model: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    mcp_ids: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)  # 逗号分隔的 MCP id
    skill_ids: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )  # 逗号分隔的 Skill id
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
