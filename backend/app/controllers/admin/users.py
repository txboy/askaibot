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
from app.auth import create_admin_token, get_current_admin, require_super
from app.common import get_setting, mask_key
from app.config import config
from app.database import get_db
from app.security import hash_password, verify_password
from app.services.audit import audit

router = APIRouter()
__all__ = ["delete_user", "list_users", "assign_user_department"]


def _platform(u: models.User) -> str:
    if u.feishu_userid:
        return "feishu"
    if u.dingtalk_userid:
        return "dingtalk"
    if u.wecom_userid:
        return "wecom"
    if u.phone:
        return "phone"
    return ""


def _user_out(db: Session, u: models.User) -> schemas.AdminUserOut:
    today_start = datetime.combine(datetime.now().date(), time.min)
    department_name = None
    if u.department_id:
        d = db.get(models.Department, u.department_id)
        department_name = d.name if d else None
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
        platform=_platform(u),
        department_id=u.department_id,
        department_name=department_name,
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
    q = db.query(models.User)
    if admin is not None and admin.role == "dept":
        q = q.filter(models.User.department_id == admin.department_id)
    users = q.order_by(models.User.created_at.desc()).all()
    return [_user_out(db, u) for u in users]


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    audit(
        db,
        admin,
        action="user.delete",
        target_type="user",
        target_id=user.id,
        summary=f"删除用户 {user.nickname}",
    )
    db.query(models.UserGroupMember).filter(
        models.UserGroupMember.user_id == user.id
    ).delete(synchronize_session=False)
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


@router.put("/users/{user_id}/department")
def assign_user_department(
    user_id: int,
    payload: dict,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    department_id = payload.get("department_id") or None
    if department_id and not db.get(models.Department, int(department_id)):
        raise HTTPException(status_code=404, detail="部门不存在")
    user.department_id = int(department_id) if department_id else None
    db.commit()
    audit(
        db,
        admin,
        action="user.assign_department",
        target_type="user",
        target_id=user.id,
        summary=f"分配用户 {user.nickname} 到部门 {department_id or '未分配'}",
    )
    db.commit()
    return {"ok": True}
