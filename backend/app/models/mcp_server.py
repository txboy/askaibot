from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr
from ..database import Base


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    transport: Mapped[str] = mapped_column(String(500), default="http")  # http / stdio
    url: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    headers: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    command: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    args: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    env: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    mode: Mapped[str] = mapped_column(String(500), default="llm")  # llm / frontend
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    scope: Mapped[str] = mapped_column(String(500), default="global")  # global / group
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
