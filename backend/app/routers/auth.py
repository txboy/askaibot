import os
from datetime import datetime, timedelta
import random
import uuid
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_token, get_current_user
from ..common import get_setting
from ..config import config
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_sms_codes: dict[str, dict] = {}


@router.post("/sms/send")
def sms_send(payload: schemas.SMSRequest, db: Session = Depends(get_db)):
    setting = get_setting(db)
    if config.sms_mock and setting.debug_mode:
        code = f"{random.randint(0, 999999):06d}"
        _sms_codes[payload.phone] = {
            "code": code,
            "expires": datetime.now() + timedelta(minutes=5),
        }
        return {"message": "验证码已发送", "debug_code": code}

    if not setting.sms_provider:
        raise HTTPException(status_code=400, detail="短信服务未配置")
    code = f"{random.randint(0, 999999):06d}"
    _sms_codes[payload.phone] = {
        "code": code,
        "expires": datetime.now() + timedelta(minutes=5),
    }
    try:
        from ..sms import send_sms

        send_sms(setting, payload.phone, code)
    except Exception as exc:
        _sms_codes.pop(payload.phone, None)
        raise HTTPException(status_code=400, detail=f"短信发送失败：{exc}")
    return {"message": "验证码已发送"}


@router.post("/sms/verify", response_model=schemas.TokenResponse)
def sms_verify(payload: schemas.SMSVerifyRequest, db: Session = Depends(get_db)):
    entry = _sms_codes.get(payload.phone)
    if not entry or entry["code"] != payload.code or entry["expires"] < datetime.now():
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    _sms_codes.pop(payload.phone, None)

    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user:
        user = models.User(phone=payload.phone, nickname=f"用户{payload.phone[-4:]}")
        db.add(user)
        db.commit()
        db.refresh(user)

    return schemas.TokenResponse(token=create_token(user.id), user=user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.put("/profile", response_model=schemas.UserOut)
def update_profile(
    payload: schemas.ProfileUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.nickname is not None:
        nickname = payload.nickname.strip()
        if not nickname:
            raise HTTPException(status_code=400, detail="昵称不能为空")
        if len(nickname) > 20:
            raise HTTPException(status_code=400, detail="昵称最长 20 个字")
        user.nickname = nickname
    if payload.assistant_name is not None:
        aname = payload.assistant_name.strip()
        if len(aname) > 20:
            raise HTTPException(status_code=400, detail="助手名最长 20 个字")
        user.assistant_name = aname
    db.commit()
    db.refresh(user)
    return user


@router.post("/avatar", response_model=schemas.UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    target: str = "user",
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > config.max_upload_size:
        raise HTTPException(status_code=413, detail="文件过大")
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")

    ext = os.path.splitext(file.filename or "avatar.png")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        raise HTTPException(status_code=400, detail="仅支持图片文件")

    os.makedirs(config.upload_dir, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(config.upload_dir, stored), "wb") as f:
        f.write(data)

    if target == "assistant":
        old = user.assistant_avatar
        user.assistant_avatar = stored
    else:
        old = user.avatar
        user.avatar = stored

    if old:
        old_path = os.path.join(config.upload_dir, old)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    db.commit()
    db.refresh(user)
    return user


def _avatar_response(path: str) -> Response:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="头像已丢失")
    ext = os.path.splitext(path)[1].lower()
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


@router.get("/avatar/{user_id}")
def get_avatar(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user or not user.avatar:
        raise HTTPException(status_code=404, detail="无头像")
    return _avatar_response(os.path.join(config.upload_dir, user.avatar))


@router.get("/assistant-avatar/{user_id}")
def get_assistant_avatar(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user or not user.assistant_avatar:
        raise HTTPException(status_code=404, detail="无助手头像")
    return _avatar_response(os.path.join(config.upload_dir, user.assistant_avatar))


@router.put("/phone", response_model=schemas.UserOut)
def update_phone(
    payload: schemas.PhoneUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    phone = payload.phone.strip()
    entry = _sms_codes.get(phone)
    if not entry or entry["code"] != payload.code or entry["expires"] < datetime.now():
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    existing = (
        db.query(models.User)
        .filter(models.User.phone == phone, models.User.id != user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该手机号已被其他用户绑定")

    _sms_codes.pop(phone, None)
    user.phone = phone
    db.commit()
    db.refresh(user)
    return user


@router.get("/wecom/qrcode")
def wecom_qrcode(db: Session = Depends(get_db)):
    setting = get_setting(db)
    if _wecom_is_real(setting):
        state = str(uuid.uuid4())
        url = _wecom_authorize_url(setting, state)
        return {"mode": "real", "login_url": url, "state": state}
    if not setting.debug_mode:
        return {"mode": "disabled", "login_url": "", "mock_code": ""}
    code = f"mock-{uuid.uuid4().hex}"
    login_url = f"/api/auth/wecom/callback?code={code}"
    return {
        "mode": "mock",
        "login_url": login_url,
        "mock_code": code,
    }


@router.get("/wecom/oauth")
def wecom_oauth(db: Session = Depends(get_db), state: str = ""):
    setting = get_setting(db)
    if _wecom_is_real(setting):
        state = state or str(uuid.uuid4())
        return RedirectResponse(_wecom_authorize_url(setting, state))
    return RedirectResponse(f"{config.frontend_url}/login")


@router.get("/wecom/callback")
async def wecom_callback(code: str, db: Session = Depends(get_db)):
    setting = get_setting(db)
    if _wecom_is_real(setting):
        try:
            userid = await _wecom_exchange_userid(setting, code)
        except HTTPException as exc:
            return RedirectResponse(
                f"{_wecom_base(setting)}/login?error={quote(str(exc.detail), safe='')}"
            )
        if not userid:
            return RedirectResponse(
                f"{_wecom_base(setting)}/login?error={quote('无法识别企业微信身份（可能不在应用可见范围）', safe='')}"
            )
        nickname = f"企微·{userid[-6:]}"
    else:
        if not setting.debug_mode:
            raise HTTPException(status_code=400, detail="未开启模拟登录")
        userid = f"mock-{code}"
        nickname = "企微用户"

    user = db.query(models.User).filter(models.User.wecom_userid == userid).first()
    if not user:
        user = models.User(wecom_userid=userid, nickname=nickname)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_token(user.id)
    return RedirectResponse(f"{_wecom_base(setting)}/login?token={token}")


def _wecom_is_real(setting) -> bool:
    return bool(
        setting.wecom_corp_id and setting.wecom_secret and setting.wecom_agent_id
    )


def _wecom_base(setting) -> str:
    base = (setting.wecom_redirect or config.frontend_url).rstrip("/")
    if base.endswith("/api/auth/wecom/callback"):
        base = base[: -len("/api/auth/wecom/callback")].rstrip("/")
    return base


def _wecom_callback_url(setting) -> str:
    return f"{_wecom_base(setting)}/api/auth/wecom/callback"


def _wecom_authorize_url(setting, state: str) -> str:
    redirect = _wecom_callback_url(setting)
    return (
        "https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={setting.wecom_corp_id}"
        f"&redirect_uri={quote(redirect, safe='')}"
        "&response_type=code"
        "&scope=snsapi_base"
        f"&agentid={setting.wecom_agent_id}"
        f"&state={state}"
        "#wechat_redirect"
    )


async def _wecom_exchange_userid(setting, code: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={
                "corpid": setting.wecom_corp_id,
                "corpsecret": setting.wecom_secret,
            },
        )
        token_data = token_resp.json()
        if token_data.get("errcode") != 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"企业微信 access_token 获取失败：errcode={token_data.get('errcode')} "
                    f"errmsg={token_data.get('errmsg')}"
                ),
            )

        info_resp = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo",
            params={"access_token": token_data["access_token"], "code": code},
        )
        info = info_resp.json()
        if info.get("errcode") != 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"企业微信用户信息获取失败：errcode={info.get('errcode')} "
                    f"errmsg={info.get('errmsg')}"
                ),
            )
        return info.get("userid", "")
