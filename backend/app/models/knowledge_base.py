from datetime import datetime

from sqlalchemy import Identity, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr
from ..database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    provider: Mapped[str] = mapped_column(String(500), default="dify")  # dify / ragflow
    base_url: Mapped[str] = mapped_column(String(500))
    api_key: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    dataset_ids: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)  # 逗号分隔
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    mode: Mapped[str] = mapped_column(String(500), default="frontend")  # frontend / llm
    description: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    scope: Mapped[str] = mapped_column(String(500), default="global")  # global / group
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
