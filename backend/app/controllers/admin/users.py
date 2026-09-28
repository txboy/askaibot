import json
import os
import shutil
import uuid
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.services import mcp as mcp_core
from app.services import skills as skill_core
from app.services.kb import retrieve_kb
from app.auth import create_admin_token, get_current_admin
from app.common import get_setting, mask_key
from app.config import config
from app.database import get_db
from app.security import hash_password, verify_password

router = APIRouter()
__all__ = ["delete_user", "list_users"]

def _user_out(db: Session, u: models.User) -> schemas.AdminUserOut:
    today_start = datetime.combine(datetime.now().date(), time.min)
    conv_count = (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == u.id)
        .count()
    )
    joined = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .join(
            models.Conversation,
            models.Message.conversation_id == models.Conversation.id,
        )
        .filter(models.Conversation.user_id == u.id)
    )
    total = joined.scalar()
    today = joined.filter(models.Message.created_at >= today_start).scalar()
    last_active = (
        db.query(func.max(models.Message.created_at))
        .join(
            models.Conversation,
            models.Message.conversation_id == models.Conversation.id,
        )
        .filter(models.Conversation.user_id == u.id)
        .scalar()
    )
    return schemas.AdminUserOut(
        id=u.id,
        nickname=u.nickname,
        phone=u.phone,
        created_at=u.created_at,
        conversation_count=conv_count,
        last_active=last_active,
        total_tokens=total,
        today_tokens=today,
    )

@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [_user_out(db, u) for u in users]

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    conv_ids = [
        c.id
        for c in db.query(models.Conversation)
        .filter(models.Conversation.user_id == user.id)
        .all()
    ]
    attachments = (
        db.query(models.Attachment).filter(models.Attachment.user_id == user.id).all()
    )
    for att in attachments:
        old = os.path.join(config.upload_dir, att.stored_name)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    if conv_ids:
        db.query(models.Message).filter(
            models.Message.conversation_id.in_(conv_ids)
        ).delete(synchronize_session=False)
    db.query(models.Attachment).filter(models.Attachment.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(models.Conversation).filter(models.Conversation.user_id == user.id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()
    return {"ok": True}