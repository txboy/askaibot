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
__all__ = ["get_dingtalk", "get_feishu", "get_wecom", "update_dingtalk", "update_feishu", "update_wecom"]

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

def _dingtalk_out(setting: models.Setting) -> schemas.DingtalkOut:
    return schemas.DingtalkOut(
        app_key=setting.dingtalk_app_key or "",
        agent_id=setting.dingtalk_agent_id or "",
        redirect=setting.dingtalk_redirect or "",
        app_secret_set=bool(setting.dingtalk_app_secret),
    )

@router.get("/dingtalk", response_model=schemas.DingtalkOut)
def get_dingtalk(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _dingtalk_out(get_setting(db))

@router.put("/dingtalk", response_model=schemas.DingtalkOut)
def update_dingtalk(
    payload: schemas.DingtalkUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.app_key is not None:
        setting.dingtalk_app_key = payload.app_key
    if payload.app_secret:
        setting.dingtalk_app_secret = payload.app_secret
    if payload.agent_id is not None:
        setting.dingtalk_agent_id = payload.agent_id
    if payload.redirect is not None:
        setting.dingtalk_redirect = payload.redirect
    db.commit()
    db.refresh(setting)
    return _dingtalk_out(setting)

def _feishu_out(setting: models.Setting) -> schemas.FeishuOut:
    return schemas.FeishuOut(
        app_id=setting.feishu_app_id or "",
        redirect=setting.feishu_redirect or "",
        app_secret_set=bool(setting.feishu_app_secret),
    )

@router.get("/feishu", response_model=schemas.FeishuOut)
def get_feishu(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _feishu_out(get_setting(db))

@router.put("/feishu", response_model=schemas.FeishuOut)
def update_feishu(
    payload: schemas.FeishuUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.app_id is not None:
        setting.feishu_app_id = payload.app_id
    if payload.app_secret:
        setting.feishu_app_secret = payload.app_secret
    if payload.redirect is not None:
        setting.feishu_redirect = payload.redirect
    db.commit()
    db.refresh(setting)
    return _feishu_out(setting)