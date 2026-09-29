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
__all__ = [
    "create_wecom_bot",
    "delete_wecom_bot",
    "list_wecom_bots",
    "update_wecom_bot",
]


def _bot_callback_url(db: Session, bot_id: int, provider: str = "wecom") -> str:
    if provider == "dingtalk":
        base = (get_setting(db).dingtalk_redirect or config.frontend_url).rstrip("/")
        return f"{base}/api/dingtalk/bot/{bot_id}/callback"
    if provider == "feishu":
        base = (get_setting(db).feishu_redirect or config.frontend_url).rstrip("/")
        return f"{base}/api/feishu/bot/{bot_id}/callback"
    base = (get_setting(db).wecom_redirect or config.frontend_url).rstrip("/")
    return f"{base}/api/wecom/bot/{bot_id}/callback"


def _bot_out(bot: models.WecomBot, db: Session) -> schemas.WecomBotOut:
    return schemas.WecomBotOut(
        id=bot.id,
        name=bot.name,
        provider=bot.provider,
        corp_id=bot.corp_id,
        agent_id=bot.agent_id,
        token_masked=mask_key(bot.token),
        aes_key_set=bool(bot.aes_key),
        kb_ids=bot.kb_ids,
        mcp_ids=bot.mcp_ids,
        skill_ids=bot.skill_ids,
        web_search=bot.web_search,
        endpoint_id=bot.endpoint_id,
        model=bot.model,
        enabled=bot.enabled,
        callback_url=_bot_callback_url(db, bot.id, bot.provider),
        system_prompt=bot.system_prompt,
    )


@router.get("/wecom-bots", response_model=list[schemas.WecomBotOut])
def list_wecom_bots(
    provider: str = "wecom",
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.WecomBot)
    if provider:
        q = q.filter(models.WecomBot.provider == provider)
    return [_bot_out(b, db) for b in q.all()]


@router.post("/wecom-bots", response_model=schemas.WecomBotOut)
def create_wecom_bot(
    payload: schemas.WecomBotCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bot = models.WecomBot(
        name=payload.name,
        provider=payload.provider or "wecom",
        corp_id=payload.corp_id or "",
        secret=payload.secret or "",
        agent_id=payload.agent_id or "",
        token=payload.token or "",
        aes_key=payload.aes_key or "",
        kb_ids=payload.kb_ids or "",
        mcp_ids=payload.mcp_ids or "",
        web_search=payload.web_search or 0,
        endpoint_id=payload.endpoint_id,
        model=payload.model or "",
        enabled=payload.enabled or 1,
        system_prompt=payload.system_prompt or "",
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
    for field in (
        "name",
        "provider",
        "corp_id",
        "agent_id",
        "token",
        "aes_key",
        "kb_ids",
        "mcp_ids",
        "model",
        "system_prompt",
    ):
        val = getattr(payload, field)
        if val is not None:
            # token/aes_key 为空串时视为“不修改”，避免编辑时误清空
            if field in ("token", "aes_key") and not val:
                continue
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
