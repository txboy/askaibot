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
__all__ = [
    "admin_access",
    "admin_get_debug",
    "admin_get_theme",
    "admin_save_debug",
    "admin_save_theme",
    "change_password",
    "delete_assistant_avatar",
    "delete_favicon",
    "delete_logo",
    "get_system",
    "logo_status",
    "stats",
    "update_system",
    "upload_assistant_avatar",
    "upload_favicon",
    "upload_logo",
]

_SECRET_HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "token",
    "key",
    "secret",
    "x-auth-token",
}


@router.get("/stats")
def stats(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    total_tokens = db.query(func.coalesce(func.sum(models.Message.tokens), 0)).scalar()
    today_start = datetime.combine(datetime.now().date(), time.min)
    today_tokens = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .filter(models.Message.created_at >= today_start)
        .scalar()
    )
    month_start = datetime(datetime.now().year, datetime.now().month, 1)
    month_tokens = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .filter(models.Message.created_at >= month_start)
        .scalar()
    )
    return {
        "users": db.query(models.User).count(),
        "conversations": db.query(models.Conversation).count(),
        "messages": db.query(models.Message).count(),
        "endpoints": db.query(models.ApiEndpoint).count(),
        "attachments": db.query(models.Attachment).count(),
        "total_tokens": total_tokens,
        "today_tokens": today_tokens,
        "month_tokens": month_tokens,
    }


@router.get("/system", response_model=schemas.SystemOut)
def get_system(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return schemas.SystemOut(
        site_title=setting.site_title or "askai",
        theme=setting.theme,
        debug_mode=bool(setting.debug_mode),
        favicon_set=bool(setting.favicon_path),
        admin_secret_enabled=bool(setting.admin_secret_enabled),
        admin_secret=setting.admin_secret,
        assistant_name=setting.assistant_name or "askai",
        assistant_avatar_set=bool(setting.assistant_avatar),
        system_prompt=setting.system_prompt or "",
        token_limit_daily=setting.token_limit_daily,
    )


@router.put("/system", response_model=schemas.SystemOut)
def update_system(
    payload: schemas.SystemUpdate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.site_title is not None:
        setting.site_title = payload.site_title
    if payload.admin_secret_enabled is not None:
        setting.admin_secret_enabled = 1 if payload.admin_secret_enabled else 0
    if payload.admin_secret is not None:
        setting.admin_secret = payload.admin_secret
    if payload.assistant_name is not None:
        setting.assistant_name = payload.assistant_name.strip() or "askai"
    if payload.system_prompt is not None:
        setting.system_prompt = payload.system_prompt
    if payload.token_limit_daily is not None:
        setting.token_limit_daily = payload.token_limit_daily or None
    db.commit()
    db.refresh(setting)
    audit(
        db,
        admin,
        action="system.update",
        target_type="system",
        target_id=0,
        summary=f"更新系统设置 (title={setting.site_title})",
    )
    db.commit()
    return schemas.SystemOut(
        site_title=setting.site_title,
        theme=setting.theme,
        debug_mode=bool(setting.debug_mode),
        favicon_set=bool(setting.favicon_path),
        admin_secret_enabled=bool(setting.admin_secret_enabled),
        admin_secret=setting.admin_secret,
        assistant_name=setting.assistant_name or "askai",
        assistant_avatar_set=bool(setting.assistant_avatar),
        system_prompt=setting.system_prompt or "",
        token_limit_daily=setting.token_limit_daily,
    )


@router.get("/theme")
def admin_get_theme(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    return {"theme": get_setting(db).theme}


@router.put("/theme")
def admin_save_theme(
    payload: schemas.ThemeUpdate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    setting.theme = payload.theme
    db.commit()
    db.refresh(setting)
    return {"theme": setting.theme}


@router.get("/debug")
def admin_get_debug(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    return {"debug_mode": bool(get_setting(db).debug_mode)}


@router.put("/debug")
def admin_save_debug(
    payload: schemas.DebugUpdate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    setting.debug_mode = 1 if payload.debug_mode else 0
    db.commit()
    db.refresh(setting)
    return {"debug_mode": bool(setting.debug_mode)}


@router.get("/access")
def admin_access(r: str = "", db: Session = Depends(get_db)):
    setting = get_setting(db)
    if setting.admin_secret_enabled:
        if r != setting.admin_secret:
            raise HTTPException(status_code=404, detail="页面不存在")
    return {"ok": True}


@router.post("/favicon")
async def upload_favicon(
    file: UploadFile = File(...),
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Favicon 文件过大")
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    os.makedirs(config.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "favicon")[1].lower() or ".ico"
    stored = f"favicon_{uuid.uuid4().hex}{ext}"
    path = os.path.join(config.upload_dir, stored)
    with open(path, "wb") as f:
        f.write(data)

    setting = get_setting(db)
    if setting.favicon_path:
        old = os.path.join(config.upload_dir, setting.favicon_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    setting.favicon_path = stored
    db.commit()
    return {"favicon_set": True, "url": "/api/favicon"}


@router.delete("/favicon")
def delete_favicon(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if setting.favicon_path:
        old = os.path.join(config.upload_dir, setting.favicon_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
        setting.favicon_path = ""
        db.commit()
    return {"favicon_set": False}


@router.post("/assistant-avatar")
async def upload_assistant_avatar(
    file: UploadFile = File(...),
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片文件过大")
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    os.makedirs(config.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "assistant_avatar")[1].lower()
    stored = f"assistant_avatar_{uuid.uuid4().hex}{ext}"
    path = os.path.join(config.upload_dir, stored)
    with open(path, "wb") as f:
        f.write(data)

    setting = get_setting(db)
    if setting.assistant_avatar:
        old = os.path.join(config.upload_dir, setting.assistant_avatar)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    setting.assistant_avatar = stored
    db.commit()
    return {"assistant_avatar_set": True, "url": "/api/assistant-avatar"}


@router.delete("/assistant-avatar")
def delete_assistant_avatar(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if setting.assistant_avatar:
        old = os.path.join(config.upload_dir, setting.assistant_avatar)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
        setting.assistant_avatar = ""
        db.commit()
    return {"assistant_avatar_set": False}


@router.get("/logo")
def logo_status(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return {"logo_set": bool(setting.logo_path)}


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo 文件过大")
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    os.makedirs(config.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "logo")[1].lower() or ".png"
    stored = f"logo_{uuid.uuid4().hex}{ext}"
    path = os.path.join(config.upload_dir, stored)
    with open(path, "wb") as f:
        f.write(data)

    setting = get_setting(db)
    if setting.logo_path:
        old = os.path.join(config.upload_dir, setting.logo_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    setting.logo_path = stored
    db.commit()
    return {"logo_set": True, "url": "/api/logo"}


@router.delete("/logo")
def delete_logo(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if setting.logo_path:
        old = os.path.join(config.upload_dir, setting.logo_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
        setting.logo_path = ""
        db.commit()
    return {"logo_set": False}


@router.put("/password")
def change_password(
    payload: schemas.AdminPasswordChange,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    admin.password_hash = hash_password(payload.new_password)
    audit(
        db,
        admin,
        action="admin.password_change",
        target_type="admin",
        target_id=admin.id,
        summary=f"修改密码 {admin.username}",
    )
    db.commit()
    return {"ok": True}
