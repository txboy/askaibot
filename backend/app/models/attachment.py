from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=True, index=True
    )
    message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("messages.id"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String)
    stored_name: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String, default="")
    kind: Mapped[str] = mapped_column(String, default="text")  # image / text / doc
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
