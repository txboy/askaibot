from datetime import datetime

from sqlalchemy import Identity, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class BotEvent(Base):
    __tablename__ = "bot_events"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("wecom_bots.id"))
    event_id: Mapped[str] = mapped_column(String(191), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
