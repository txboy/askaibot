from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .types import OrEmptyStr, OrEmptyText
from ..database import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    dir_path: Mapped[str] = mapped_column(
        OrEmptyStr(255), default="", nullable=True
    )  # upload_dir 内的技能包目录
    content: Mapped[str] = mapped_column(
        OrEmptyText(), default="", nullable=True
    )  # SKILL.md 正文（注入系统提示词）
    tools: Mapped[str] = mapped_column(Text, default="[]")  # JSON：工具声明列表
    scope: Mapped[str] = mapped_column(String(500), default="global")  # global / user
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SkillAccess(Base):
    __tablename__ = "skill_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
