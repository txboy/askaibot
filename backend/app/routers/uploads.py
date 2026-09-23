import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..common import get_setting
from ..config import config
from ..database import get_db
from ..filetools import detect_kind, extract_text

router = APIRouter(tags=["files"])


def _upload_dir() -> str:
    os.makedirs(config.upload_dir, exist_ok=True)
    return config.upload_dir


@router.post("/upload", response_model=schemas.AttachmentOut)
async def upload_file(
    file: UploadFile = File(...),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > config.max_upload_size:
        raise HTTPException(status_code=413, detail="文件过大")

    filename = file.filename or "file"
    ext = os.path.splitext(filename)[1].lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(_upload_dir(), stored_name)
    with open(path, "wb") as f:
        f.write(data)

    content_type = file.content_type or "application/octet-stream"
    kind = detect_kind(filename, content_type)
    text = extract_text(filename, content_type, data)

    attachment = models.Attachment(
        user_id=user.id,
        filename=filename,
        stored_name=stored_name,
        content_type=content_type,
        kind=kind,
        extracted_text=text,
        size=len(data),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/files/{attachment_id}")
def get_file(
    attachment_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = db.get(models.Attachment, attachment_id)
    if not attachment or attachment.user_id != user.id:
        raise HTTPException(status_code=404, detail="文件不存在")

    path = os.path.join(config.upload_dir, attachment.stored_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    data = open(path, "rb").read()
    return Response(
        content=data,
        media_type=attachment.content_type or "application/octet-stream",
    )


@router.get("/logo")
def get_logo(db: Session = Depends(get_db)):
    setting = get_setting(db)
    if not setting.logo_path:
        raise HTTPException(status_code=404, detail="未设置 Logo")
    path = os.path.join(config.upload_dir, setting.logo_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Logo 已丢失")
    return FileResponse(path)


@router.get("/favicon")
def get_favicon(db: Session = Depends(get_db)):
    setting = get_setting(db)
    if not setting.favicon_path:
        raise HTTPException(status_code=404, detail="未设置 favicon")
    path = os.path.join(config.upload_dir, setting.favicon_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="favicon 已丢失")
    return FileResponse(path)


@router.get("/assistant-avatar")
def get_default_assistant_avatar(db: Session = Depends(get_db)):
    setting = get_setting(db)
    if not setting.assistant_avatar:
        raise HTTPException(status_code=404, detail="未设置助手默认头像")
    path = os.path.join(config.upload_dir, setting.assistant_avatar)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="助手默认头像已丢失")
    ext = os.path.splitext(setting.assistant_avatar)[1].lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }.get(ext, "application/octet-stream")
    data = open(path, "rb").read()
    return Response(content=data, media_type=media_type)


@router.get("/config/site")
def get_site(db: Session = Depends(get_db)):
    setting = get_setting(db)
    return {
        "site_title": setting.site_title or "askai",
        "assistant_name": setting.assistant_name or "askai",
        "assistant_avatar_url": (
            f"/api/assistant-avatar?v={setting.assistant_avatar}"
            if setting.assistant_avatar
            else ""
        ),
        "favicon_url": "/api/favicon" if setting.favicon_path else "/favicon.svg",
    }


@router.get("/config/theme")
def get_theme(db: Session = Depends(get_db)):
    setting = get_setting(db)
    return {"theme": setting.theme}


@router.get("/config/debug")
def get_debug(db: Session = Depends(get_db)):
    setting = get_setting(db)
    return {"debug_mode": bool(setting.debug_mode)}


@router.get("/config/sms")
def get_sms_enabled(db: Session = Depends(get_db)):
    setting = get_setting(db)
    enabled = bool((config.sms_mock and setting.debug_mode) or setting.sms_provider)
    return {"enabled": enabled}


@router.get("/config/search")
def get_search_enabled(db: Session = Depends(get_db)):
    setting = get_setting(db)
    return {"enabled": bool(setting.search_provider)}


@router.get("/config/wecom")
def get_wecom_enabled(db: Session = Depends(get_db)):
    setting = get_setting(db)
    real = bool(
        setting.wecom_corp_id and setting.wecom_secret and setting.wecom_agent_id
    )
    return {"enabled": bool(real or setting.debug_mode)}
