from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nickname: Mapped[str] = mapped_column(String, default="用户")
    avatar: Mapped[str] = mapped_column(String, default="")
    assistant_name: Mapped[str] = mapped_column(String, default="")
    assistant_avatar: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    wecom_userid: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    dingtalk_userid: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    feishu_userid: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
