from datetime import datetime

from sqlalchemy import Identity, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr, OrEmptyText
from ..database import Base


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    base_url: Mapped[str] = mapped_column(String(500))
    api_key: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    models: Mapped[str] = mapped_column(OrEmptyText(), default="", nullable=True)  # 逗号/换行分隔的模型列表
    system_prompt: Mapped[str] = mapped_column(OrEmptyText(), default="", nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    scope: Mapped[str] = mapped_column(String(500), default="global")  # global / group
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
