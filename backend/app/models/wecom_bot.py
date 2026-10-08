from datetime import datetime

from sqlalchemy import Identity, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr, OrEmptyText
from ..database import Base


class WecomBot(Base):
    __tablename__ = "wecom_bots"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    provider: Mapped[str] = mapped_column(
        String(500), default="wecom"
    )  # wecom / dingtalk
    corp_id: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    secret: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    agent_id: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    token: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    aes_key: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    kb_ids: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)  # 逗号分隔
    mcp_ids: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)  # 逗号分隔
    skill_ids: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)  # 逗号分隔
    web_search: Mapped[int] = mapped_column(Integer, default=0)
    system_prompt: Mapped[str] = mapped_column(OrEmptyText(), default="", nullable=True)
    endpoint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("api_endpoints.id"), nullable=True
    )
    model: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
