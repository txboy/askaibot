from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class WecomBot(Base):
    __tablename__ = "wecom_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String, default="wecom")  # wecom / dingtalk
    corp_id: Mapped[str] = mapped_column(String, default="")
    secret: Mapped[str] = mapped_column(String, default="")
    agent_id: Mapped[str] = mapped_column(String, default="")
    token: Mapped[str] = mapped_column(String, default="")
    aes_key: Mapped[str] = mapped_column(String, default="")
    kb_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    mcp_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    skill_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    web_search: Mapped[int] = mapped_column(Integer, default=0)
    endpoint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("api_endpoints.id"), nullable=True
    )
    model: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
