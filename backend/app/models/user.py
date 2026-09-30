from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(500), default="用户")
    avatar: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    assistant_name: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    assistant_avatar: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    phone: Mapped[str | None] = mapped_column(String(191), nullable=True)
    wecom_userid: Mapped[str | None] = mapped_column(String(191), nullable=True)
    dingtalk_userid: Mapped[str | None] = mapped_column(String(191), nullable=True)
    feishu_userid: Mapped[str | None] = mapped_column(String(191), nullable=True)
    agreed_agreement_ids: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    agreed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_limit_daily: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 这些标识列允许为空，但非空时需唯一。MSSQL 的唯一索引不允许重复 NULL，
    # 因此用过滤唯一索引（仅对非空值唯一），其余方言（SQLite/MySQL/PG/Oracle）
    # 本身允许多个 NULL，维持普通唯一索引即可。
    __table_args__ = (
        Index(
            "ix_users_phone",
            "phone",
            unique=True,
            mssql_where=text("phone IS NOT NULL"),
        ),
        Index(
            "ix_users_wecom_userid",
            "wecom_userid",
            unique=True,
            mssql_where=text("wecom_userid IS NOT NULL"),
        ),
        Index(
            "ix_users_dingtalk_userid",
            "dingtalk_userid",
            unique=True,
            mssql_where=text("dingtalk_userid IS NOT NULL"),
        ),
        Index(
            "ix_users_feishu_userid",
            "feishu_userid",
            unique=True,
            mssql_where=text("feishu_userid IS NOT NULL"),
        ),
    )
