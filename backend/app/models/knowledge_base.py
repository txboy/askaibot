from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String, default="dify")  # dify / ragflow
    base_url: Mapped[str] = mapped_column(String)
    api_key: Mapped[str] = mapped_column(String, default="")
    dataset_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    mode: Mapped[str] = mapped_column(String, default="frontend")  # frontend / llm
    description: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
