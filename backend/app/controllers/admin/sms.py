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
__all__ = ["get_sms", "update_sms"]

def _sms_out(setting: models.Setting) -> schemas.SmsOut:
    return schemas.SmsOut(
        provider=setting.sms_provider or "",
        access_key_id=setting.sms_access_key_id or "",
        sign_name=setting.sms_sign_name or "",
        template_code=setting.sms_template_code or "",
        region=setting.sms_region or "",
        sdk_app_id=setting.sms_sdk_app_id or "",
        secret_set=bool(setting.sms_secret),
        captcha_enabled=bool(setting.sms_captcha_enabled),
        captcha_provider=setting.sms_captcha_provider or "builtin",
        cooldown=setting.sms_cooldown or 60,
        geetest_captcha_id=setting.geetest_captcha_id or "",
        geetest_key_set=bool(setting.geetest_captcha_key),
        tencent_captcha_app_id=setting.tencent_captcha_app_id or "",
        tencent_key_set=bool(setting.tencent_captcha_app_secret_key),
        aliyun_access_key_id=setting.aliyun_captcha_access_key_id or "",
        aliyun_secret_set=bool(setting.aliyun_captcha_access_key_secret),
        aliyun_scene_id=setting.aliyun_captcha_scene_id or "",
    )

@router.get("/sms", response_model=schemas.SmsOut)
def get_sms(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _sms_out(get_setting(db))

@router.put("/sms", response_model=schemas.SmsOut)
def update_sms(
    payload: schemas.SmsUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.provider is not None:
        setting.sms_provider = payload.provider
    if payload.access_key_id is not None:
        setting.sms_access_key_id = payload.access_key_id
    if payload.secret:
        setting.sms_secret = payload.secret
    if payload.sign_name is not None:
        setting.sms_sign_name = payload.sign_name
    if payload.template_code is not None:
        setting.sms_template_code = payload.template_code
    if payload.region is not None:
        setting.sms_region = payload.region
    if payload.sdk_app_id is not None:
        setting.sms_sdk_app_id = payload.sdk_app_id
    if payload.captcha_enabled is not None:
        setting.sms_captcha_enabled = 1 if payload.captcha_enabled else 0
    if payload.captcha_provider is not None:
        setting.sms_captcha_provider = payload.captcha_provider
    if payload.cooldown is not None:
        setting.sms_cooldown = payload.cooldown
    if payload.geetest_captcha_id is not None:
        setting.geetest_captcha_id = payload.geetest_captcha_id
    if payload.geetest_captcha_key:
        setting.geetest_captcha_key = payload.geetest_captcha_key
    if payload.tencent_captcha_app_id is not None:
        setting.tencent_captcha_app_id = payload.tencent_captcha_app_id
    if payload.tencent_captcha_app_secret_key:
        setting.tencent_captcha_app_secret_key = payload.tencent_captcha_app_secret_key
    if payload.aliyun_access_key_id is not None:
        setting.aliyun_captcha_access_key_id = payload.aliyun_access_key_id
    if payload.aliyun_access_key_secret:
        setting.aliyun_captcha_access_key_secret = payload.aliyun_access_key_secret
    if payload.aliyun_scene_id is not None:
        setting.aliyun_captcha_scene_id = payload.aliyun_scene_id
    db.commit()
    db.refresh(setting)
    return _sms_out(setting)