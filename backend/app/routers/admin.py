import os
import uuid
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_admin_token, get_current_admin
from ..common import get_setting, mask_key
from ..config import config
from ..database import get_db
from ..security import hash_password, verify_password

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=schemas.AdminLoginResponse)
def admin_login(payload: schemas.AdminLoginRequest, db: Session = Depends(get_db)):
    admin = (
        db.query(models.Admin).filter(models.Admin.username == payload.username).first()
    )
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return schemas.AdminLoginResponse(token=create_admin_token(admin.username))


def _endpoint_out(e: models.ApiEndpoint) -> schemas.EndpointOut:
    return schemas.EndpointOut(
        id=e.id,
        name=e.name,
        base_url=e.base_url,
        api_key_masked=mask_key(e.api_key),
        models=e.models,
        enabled=e.enabled,
        is_default=e.is_default,
    )


@router.get("/endpoints", response_model=list[schemas.EndpointOut])
def list_endpoints(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_endpoint_out(e) for e in db.query(models.ApiEndpoint).all()]


@router.post("/endpoints", response_model=schemas.EndpointOut)
def create_endpoint(
    payload: schemas.EndpointCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = models.ApiEndpoint(
        name=payload.name,
        base_url=payload.base_url,
        api_key=payload.api_key or "",
        models=payload.models or "",
        enabled=payload.enabled or 1,
        is_default=payload.is_default or 0,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


@router.put("/endpoints/{endpoint_id}", response_model=schemas.EndpointOut)
def update_endpoint(
    endpoint_id: int,
    payload: schemas.EndpointUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = db.get(models.ApiEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    if payload.name is not None:
        endpoint.name = payload.name
    if payload.base_url is not None:
        endpoint.base_url = payload.base_url
    if payload.api_key:
        endpoint.api_key = payload.api_key
    if payload.models is not None:
        endpoint.models = payload.models
    if payload.enabled is not None:
        endpoint.enabled = payload.enabled
    if payload.is_default is not None:
        endpoint.is_default = payload.is_default
        if payload.is_default:
            db.query(models.ApiEndpoint).filter(
                models.ApiEndpoint.id != endpoint.id
            ).update({"is_default": 0})
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


@router.delete("/endpoints/{endpoint_id}")
def delete_endpoint(
    endpoint_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = db.get(models.ApiEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    db.delete(endpoint)
    db.commit()
    return {"ok": True}


@router.get("/wecom", response_model=schemas.WecomOut)
def get_wecom(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return schemas.WecomOut(
        wecom_corp_id=setting.wecom_corp_id,
        wecom_agent_id=setting.wecom_agent_id,
        wecom_redirect=setting.wecom_redirect,
        wecom_secret_set=bool(setting.wecom_secret),
    )


@router.put("/wecom", response_model=schemas.WecomOut)
def update_wecom(
    payload: schemas.WecomUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.wecom_corp_id is not None:
        setting.wecom_corp_id = payload.wecom_corp_id
    if payload.wecom_secret:
        setting.wecom_secret = payload.wecom_secret
    if payload.wecom_agent_id is not None:
        setting.wecom_agent_id = payload.wecom_agent_id
    if payload.wecom_redirect is not None:
        setting.wecom_redirect = payload.wecom_redirect
    db.commit()
    db.refresh(setting)
    return schemas.WecomOut(
        wecom_corp_id=setting.wecom_corp_id,
        wecom_agent_id=setting.wecom_agent_id,
        wecom_redirect=setting.wecom_redirect,
        wecom_secret_set=bool(setting.wecom_secret),
    )


@router.get("/search", response_model=schemas.SearchOut)
def get_search(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return schemas.SearchOut(
        provider=setting.search_provider,
        base_url=setting.search_base_url,
        auto=bool(setting.search_auto),
        api_key_set=bool(setting.search_api_key),
    )


@router.put("/search", response_model=schemas.SearchOut)
def update_search(
    payload: schemas.SearchUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.provider is not None:
        setting.search_provider = payload.provider
    if payload.api_key:
        setting.search_api_key = payload.api_key
    if payload.base_url is not None:
        setting.search_base_url = payload.base_url
    if payload.auto is not None:
        setting.search_auto = 1 if payload.auto else 0
    db.commit()
    db.refresh(setting)
    return schemas.SearchOut(
        provider=setting.search_provider,
        base_url=setting.search_base_url,
        auto=bool(setting.search_auto),
        api_key_set=bool(setting.search_api_key),
    )


def _kb_out(kb: models.KnowledgeBase) -> schemas.KnowledgeBaseOut:
    return schemas.KnowledgeBaseOut(
        id=kb.id,
        name=kb.name,
        base_url=kb.base_url,
        api_key_masked=mask_key(kb.api_key),
        description=kb.description,
        enabled=kb.enabled,
    )


@router.get("/knowledge-bases", response_model=list[schemas.KnowledgeBaseOut])
def list_knowledge_bases(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_kb_out(kb) for kb in db.query(models.KnowledgeBase).all()]


@router.post("/knowledge-bases", response_model=schemas.KnowledgeBaseOut)
def create_knowledge_base(
    payload: schemas.KnowledgeBaseCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = models.KnowledgeBase(
        name=payload.name,
        base_url=payload.base_url,
        api_key=payload.api_key or "",
        description=payload.description or "",
        enabled=payload.enabled or 1,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _kb_out(kb)


@router.put("/knowledge-bases/{kb_id}", response_model=schemas.KnowledgeBaseOut)
def update_knowledge_base(
    kb_id: int,
    payload: schemas.KnowledgeBaseUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if payload.name is not None:
        kb.name = payload.name
    if payload.base_url is not None:
        kb.base_url = payload.base_url
    if payload.api_key:
        kb.api_key = payload.api_key
    if payload.description is not None:
        kb.description = payload.description
    if payload.enabled is not None:
        kb.enabled = payload.enabled
    db.commit()
    db.refresh(kb)
    return _kb_out(kb)


@router.delete("/knowledge-bases/{kb_id}")
def delete_knowledge_base(
    kb_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    db.delete(kb)
    db.commit()
    return {"ok": True}


def _bot_callback_url(db: Session, bot_id: int) -> str:
    base = (get_setting(db).wecom_redirect or config.frontend_url).rstrip("/")
    return f"{base}/api/wecom/bot/{bot_id}/callback"


def _bot_out(bot: models.WecomBot, db: Session) -> schemas.WecomBotOut:
    return schemas.WecomBotOut(
        id=bot.id,
        name=bot.name,
        corp_id=bot.corp_id,
        agent_id=bot.agent_id,
        token_masked=mask_key(bot.token),
        aes_key_set=bool(bot.aes_key),
        kb_ids=bot.kb_ids,
        web_search=bot.web_search,
        endpoint_id=bot.endpoint_id,
        model=bot.model,
        enabled=bot.enabled,
        callback_url=_bot_callback_url(db, bot.id),
    )


@router.get("/wecom-bots", response_model=list[schemas.WecomBotOut])
def list_wecom_bots(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_bot_out(b, db) for b in db.query(models.WecomBot).all()]


@router.post("/wecom-bots", response_model=schemas.WecomBotOut)
def create_wecom_bot(
    payload: schemas.WecomBotCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bot = models.WecomBot(
        name=payload.name,
        corp_id=payload.corp_id or "",
        secret=payload.secret or "",
        agent_id=payload.agent_id or "",
        token=payload.token or "",
        aes_key=payload.aes_key or "",
        kb_ids=payload.kb_ids or "",
        web_search=payload.web_search or 0,
        endpoint_id=payload.endpoint_id,
        model=payload.model or "",
        enabled=payload.enabled or 1,
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return _bot_out(bot, db)


@router.put("/wecom-bots/{bot_id}", response_model=schemas.WecomBotOut)
def update_wecom_bot(
    bot_id: int,
    payload: schemas.WecomBotUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bot = db.get(models.WecomBot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    for field in ("name", "corp_id", "agent_id", "token", "aes_key", "kb_ids", "model"):
        val = getattr(payload, field)
        if val is not None:
            setattr(bot, field, val)
    if payload.secret:
        bot.secret = payload.secret
    if payload.web_search is not None:
        bot.web_search = payload.web_search
    if payload.endpoint_id is not None:
        bot.endpoint_id = payload.endpoint_id
    if payload.enabled is not None:
        bot.enabled = payload.enabled
    db.commit()
    db.refresh(bot)
    return _bot_out(bot, db)


@router.delete("/wecom-bots/{bot_id}")
def delete_wecom_bot(
    bot_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bot = db.get(models.WecomBot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    db.delete(bot)
    db.commit()
    return {"ok": True}


@router.get("/stats")
def stats(
    admin: models.Admin = Depends(get_current_admin),
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
    admin: models.Admin = Depends(get_current_admin),
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
    )


@router.put("/system", response_model=schemas.SystemOut)
def update_system(
    payload: schemas.SystemUpdate,
    admin: models.Admin = Depends(get_current_admin),
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
    db.commit()
    db.refresh(setting)
    return schemas.SystemOut(
        site_title=setting.site_title,
        theme=setting.theme,
        debug_mode=bool(setting.debug_mode),
        favicon_set=bool(setting.favicon_path),
        admin_secret_enabled=bool(setting.admin_secret_enabled),
        admin_secret=setting.admin_secret,
        assistant_name=setting.assistant_name or "askai",
        assistant_avatar_set=bool(setting.assistant_avatar),
    )


@router.get("/theme")
def admin_get_theme(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return {"theme": get_setting(db).theme}


@router.put("/theme")
def admin_save_theme(
    payload: schemas.ThemeUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    setting.theme = payload.theme
    db.commit()
    db.refresh(setting)
    return {"theme": setting.theme}


@router.get("/debug")
def admin_get_debug(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return {"debug_mode": bool(get_setting(db).debug_mode)}


@router.put("/debug")
def admin_save_debug(
    payload: schemas.DebugUpdate,
    admin: models.Admin = Depends(get_current_admin),
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
    admin: models.Admin = Depends(get_current_admin),
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
    admin: models.Admin = Depends(get_current_admin),
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
    admin: models.Admin = Depends(get_current_admin),
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
    admin: models.Admin = Depends(get_current_admin),
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
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return {"logo_set": bool(setting.logo_path)}


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    admin: models.Admin = Depends(get_current_admin),
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
    admin: models.Admin = Depends(get_current_admin),
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
