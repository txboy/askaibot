from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_username: Mapped[str] = mapped_column(String(500), default="")
    admin_role: Mapped[str] = mapped_column(String(500), default="")
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(500))
    target_type: Mapped[str] = mapped_column(String(500), default="")
    target_id: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(500), default="")
    user_agent: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
