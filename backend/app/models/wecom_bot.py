from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class WecomBot(Base):
    __tablename__ = "wecom_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(500))
    provider: Mapped[str] = mapped_column(String(500), default="wecom")  # wecom / dingtalk
    corp_id: Mapped[str] = mapped_column(String(500), default="")
    secret: Mapped[str] = mapped_column(String(500), default="")
    agent_id: Mapped[str] = mapped_column(String(500), default="")
    token: Mapped[str] = mapped_column(String(500), default="")
    aes_key: Mapped[str] = mapped_column(String(500), default="")
    kb_ids: Mapped[str] = mapped_column(String(500), default="")  # 逗号分隔
    mcp_ids: Mapped[str] = mapped_column(String(500), default="")  # 逗号分隔
    skill_ids: Mapped[str] = mapped_column(String(500), default="")  # 逗号分隔
    web_search: Mapped[int] = mapped_column(Integer, default=0)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    endpoint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("api_endpoints.id"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(500), default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
