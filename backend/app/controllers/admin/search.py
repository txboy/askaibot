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
from app.auth import create_admin_token, require_super
from app.common import get_setting, mask_key
from app.config import config
from app.database import get_db
from app.security import hash_password, verify_password
from app.services import groups as groups_core
from app.services.audit import audit

router = APIRouter()
__all__ = ["get_search", "update_search"]

@router.get("/search", response_model=schemas.SearchOut)
def get_search(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return schemas.SearchOut(
        provider=setting.search_provider,
        base_url=setting.search_base_url,
        auto=bool(setting.search_auto),
        api_key_set=bool(setting.search_api_key),
        scope=setting.search_scope or "global",
        group_ids=groups_core.group_ids_for_resource(db, "search", 0),
    )

@router.put("/search", response_model=schemas.SearchOut)
def update_search(
    payload: schemas.SearchUpdate,
    admin: models.Admin = Depends(require_super),
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
    if payload.scope is not None:
        setting.search_scope = payload.scope
    db.commit()
    db.refresh(setting)
    if payload.group_ids is not None:
        groups_core.set_resource_grants(db, "search", 0, payload.group_ids)
        db.commit()
    audit(
        db,
        admin,
        action="search.update",
        target_type="search",
        target_id=0,
        summary=f"更新联网搜索配置 ({payload.provider or setting.search_provider or '未配置'})",
    )
    db.commit()
    return schemas.SearchOut(
        provider=setting.search_provider,
        base_url=setting.search_base_url,
        auto=bool(setting.search_auto),
        api_key_set=bool(setting.search_api_key),
        scope=setting.search_scope or "global",
        group_ids=groups_core.group_ids_for_resource(db, "search", 0),
    )