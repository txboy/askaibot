import os
from datetime import datetime, timedelta
import random
import uuid
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app import models, schemas
from app.services import captcha as captcha_mod
from app.auth import create_token, get_current_user
from app.common import get_setting
from app.config import config
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_sms_codes: dict[str, dict] = {}


@router.get("/captcha")
def get_captcha(db: Session = Depends(get_db)):
    setting = get_setting(db)
    return captcha_mod.build_challenge(setting)


@router.post("/sms/send")
def sms_send(payload: schemas.SMSRequest, db: Session = Depends(get_db)):
    setting = get_setting(db)

    if setting.sms_captcha_enabled:
        if not captcha_mod.verify(setting, payload):
            raise HTTPException(status_code=400, detail="验证码错误或已过期")

    now = datetime.now()
    prev = _sms_codes.get(payload.phone)
    cooldown = setting.sms_cooldown or 60
    if (
        prev
        and prev.get("sent_at")
        and (now - prev["sent_at"]).total_seconds() < cooldown
    ):
        raise HTTPException(
            status_code=429, detail=f"发送过于频繁，请{cooldown}秒后再试"
        )

    if config.sms_mock and setting.debug_mode:
        code = f"{random.randint(0, 999999):06d}"
        _sms_codes[payload.phone] = {
            "code": code,
            "expires": now + timedelta(minutes=5),
            "sent_at": now,
        }
        return {"message": "验证码已发送", "debug_code": code}

    if not setting.sms_provider:
        raise HTTPException(status_code=400, detail="短信服务未配置")
    code = f"{random.randint(0, 999999):06d}"
    _sms_codes[payload.phone] = {
        "code": code,
        "expires": now + timedelta(minutes=5),
        "sent_at": now,
    }
    try:
        from app.services.sms import send_sms

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


def _dingtalk_is_real(setting) -> bool:
    return bool(setting.dingtalk_app_key and setting.dingtalk_app_secret)


def _dingtalk_base(setting) -> str:
    base = (setting.dingtalk_redirect or config.frontend_url).rstrip("/")
    if base.endswith("/api/auth/dingtalk/callback"):
        base = base[: -len("/api/auth/dingtalk/callback")].rstrip("/")
    return base


def _dingtalk_callback_url(setting) -> str:
    return f"{_dingtalk_base(setting)}/api/auth/dingtalk/callback"


def _dingtalk_authorize_url(setting, state: str) -> str:
    redirect = _dingtalk_callback_url(setting)
    return (
        "https://login.dingtalk.com/oauth2/auth"
        f"?redirect_uri={quote(redirect, safe='')}"
        "&response_type=code"
        f"&client_id={setting.dingtalk_app_key}"
        "&scope=openid"
        "&prompt=consent"
        f"&state={state}"
    )


async def _dingtalk_user_token(client_id: str, client_secret: str, code: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.dingtalk.com/v1.0/oauth2/userAccessToken",
            headers={"Content-Type": "application/json"},
            json={
                "clientId": client_id,
                "clientSecret": client_secret,
                "code": code,
                "grantType": "authorization_code",
            },
        )
        data = resp.json()
    token = data.get("accessToken")
    if not token:
        raise HTTPException(
            status_code=400,
            detail=f"钉钉登录失败：{data.get('message', '未获取到 accessToken')}",
        )
    return token


async def _dingtalk_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.dingtalk.com/v1.0/contact/users/me",
            headers={"x-acs-dingtalk-access-token": access_token},
        )
        data = resp.json()
    if not data.get("userId"):
        raise HTTPException(
            status_code=400,
            detail=f"钉钉用户信息获取失败：{data.get('message', '未获取到 userId')}",
        )
    return data


@router.get("/dingtalk/qrcode")
def dingtalk_qrcode(db: Session = Depends(get_db)):
    setting = get_setting(db)
    if _dingtalk_is_real(setting):
        state = str(uuid.uuid4())
        url = _dingtalk_authorize_url(setting, state)
        return {"mode": "real", "login_url": url, "state": state}
    if not setting.debug_mode:
        return {"mode": "disabled", "login_url": "", "mock_code": ""}
    code = f"mock-dd-{uuid.uuid4().hex}"
    login_url = f"/api/auth/dingtalk/callback?code={code}"
    return {
        "mode": "mock",
        "login_url": login_url,
        "mock_code": code,
    }


@router.get("/dingtalk/oauth")
def dingtalk_oauth(db: Session = Depends(get_db), state: str = ""):
    setting = get_setting(db)
    if _dingtalk_is_real(setting):
        state = state or str(uuid.uuid4())
        return RedirectResponse(_dingtalk_authorize_url(setting, state))
    return RedirectResponse(f"{config.frontend_url}/login")


@router.get("/dingtalk/callback")
async def dingtalk_callback(code: str, db: Session = Depends(get_db)):
    setting = get_setting(db)
    if _dingtalk_is_real(setting):
        try:
            atoken = await _dingtalk_user_token(
                setting.dingtalk_app_key, setting.dingtalk_app_secret, code
            )
            info = await _dingtalk_user_info(atoken)
        except HTTPException as exc:
            return RedirectResponse(
                f"{_dingtalk_base(setting)}/login?error={quote(str(exc.detail), safe='')}"
            )
        userid = info.get("userId", "")
        nickname = info.get("nick") or f"钉钉·{userid[-6:]}"
    else:
        if not setting.debug_mode:
            raise HTTPException(status_code=400, detail="未开启模拟登录")
        userid = f"mock-dd-{code}"
        nickname = "钉钉用户"

    if not userid:
        return RedirectResponse(
            f"{_dingtalk_base(setting)}/login?error={quote('无法识别钉钉身份', safe='')}"
        )
    user = db.query(models.User).filter(models.User.dingtalk_userid == userid).first()
    if not user:
        user = models.User(dingtalk_userid=userid, nickname=nickname)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_token(user.id)
    return RedirectResponse(f"{_dingtalk_base(setting)}/login?token={token}")


@router.post("/dingtalk/free-login", response_model=schemas.TokenResponse)
async def dingtalk_free_login(
    payload: schemas.DingtalkCodeRequest, db: Session = Depends(get_db)
):
    setting = get_setting(db)
    if _dingtalk_is_real(setting):
        atoken = await _dingtalk_user_token(
            setting.dingtalk_app_key, setting.dingtalk_app_secret, payload.code
        )
        info = await _dingtalk_user_info(atoken)
        userid = info.get("userId", "")
        nickname = info.get("nick") or f"钉钉·{userid[-6:]}"
    else:
        if not setting.debug_mode:
            raise HTTPException(status_code=400, detail="未开启模拟登录")
        userid = f"mock-dd-{payload.code}"
        nickname = "钉钉用户"

    user = db.query(models.User).filter(models.User.dingtalk_userid == userid).first()
    if not user:
        user = models.User(dingtalk_userid=userid, nickname=nickname)
        db.add(user)
        db.commit()
        db.refresh(user)
    return schemas.TokenResponse(token=create_token(user.id), user=user)


def _feishu_is_real(setting) -> bool:
    return bool(setting.feishu_app_id and setting.feishu_app_secret)


def _feishu_base(setting) -> str:
    base = (setting.feishu_redirect or config.frontend_url).rstrip("/")
    if base.endswith("/api/auth/feishu/callback"):
        base = base[: -len("/api/auth/feishu/callback")].rstrip("/")
    return base


def _feishu_callback_url(setting) -> str:
    return f"{_feishu_base(setting)}/api/auth/feishu/callback"


def _feishu_authorize_url(setting, state: str) -> str:
    redirect = _feishu_callback_url(setting)
    return (
        "https://open.feishu.cn/open-apis/authen/v1/authorize"
        f"?app_id={setting.feishu_app_id}"
        f"&redirect_uri={quote(redirect, safe='')}"
        f"&state={state}"
    )


async def _feishu_user_token(app_id: str, app_secret: str, code: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/authen/v1/access_token",
            json={
                "grant_type": "authorization_code",
                "app_id": app_id,
                "app_secret": app_secret,
                "code": code,
            },
        )
        data = resp.json()
    if data.get("code") != 0:
        raise HTTPException(
            status_code=400,
            detail=(f"飞书登录失败：code={data.get('code')} msg={data.get('msg')}"),
        )
    return data.get("data") or {}


async def _feishu_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://open.feishu.cn/open-apis/authen/v1/user_info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = resp.json()
    if data.get("code") != 0:
        raise HTTPException(
            status_code=400,
            detail=f"飞书用户信息获取失败：code={data.get('code')}",
        )
    return data.get("data") or {}


@router.get("/feishu/qrcode")
def feishu_qrcode(db: Session = Depends(get_db)):
    setting = get_setting(db)
    if _feishu_is_real(setting):
        state = str(uuid.uuid4())
        url = _feishu_authorize_url(setting, state)
        return {"mode": "real", "login_url": url, "state": state}
    if not setting.debug_mode:
        return {"mode": "disabled", "login_url": "", "mock_code": ""}
    code = f"mock-fs-{uuid.uuid4().hex}"
    login_url = f"/api/auth/feishu/callback?code={code}"
    return {
        "mode": "mock",
        "login_url": login_url,
        "mock_code": code,
    }


@router.get("/feishu/oauth")
def feishu_oauth(db: Session = Depends(get_db), state: str = ""):
    setting = get_setting(db)
    if _feishu_is_real(setting):
        state = state or str(uuid.uuid4())
        return RedirectResponse(_feishu_authorize_url(setting, state))
    return RedirectResponse(f"{config.frontend_url}/login")


async def _feishu_identity(app_id: str, app_secret: str, code: str):
    data = await _feishu_user_token(app_id, app_secret, code)
    access_token = data.get("access_token", "")
    userid = data.get("union_id") or data.get("open_id") or ""
    nickname = data.get("name") or ""
    if access_token:
        try:
            info = await _feishu_user_info(access_token)
            userid = userid or info.get("union_id") or info.get("open_id") or ""
            nickname = nickname or info.get("name") or ""
        except HTTPException:
            pass
    return userid, nickname


@router.get("/feishu/callback")
async def feishu_callback(code: str, db: Session = Depends(get_db)):
    setting = get_setting(db)
    if _feishu_is_real(setting):
        try:
            userid, nickname = await _feishu_identity(
                setting.feishu_app_id, setting.feishu_app_secret, code
            )
        except HTTPException as exc:
            return RedirectResponse(
                f"{_feishu_base(setting)}/login?error={quote(str(exc.detail), safe='')}"
            )
    else:
        if not setting.debug_mode:
            raise HTTPException(status_code=400, detail="未开启模拟登录")
        userid = f"mock-fs-{code}"
        nickname = "飞书用户"

    if not userid:
        return RedirectResponse(
            f"{_feishu_base(setting)}/login?error={quote('无法识别飞书身份', safe='')}"
        )
    nickname = nickname or f"飞书·{userid[-6:]}"
    user = db.query(models.User).filter(models.User.feishu_userid == userid).first()
    if not user:
        user = models.User(feishu_userid=userid, nickname=nickname)
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_token(user.id)
    return RedirectResponse(f"{_feishu_base(setting)}/login?token={token}")


@router.post("/feishu/free-login", response_model=schemas.TokenResponse)
async def feishu_free_login(
    payload: schemas.FeishuCodeRequest, db: Session = Depends(get_db)
):
    setting = get_setting(db)
    if _feishu_is_real(setting):
        userid, nickname = await _feishu_identity(
            setting.feishu_app_id, setting.feishu_app_secret, payload.code
        )
    else:
        if not setting.debug_mode:
            raise HTTPException(status_code=400, detail="未开启模拟登录")
        userid = f"mock-fs-{payload.code}"
        nickname = "飞书用户"

    if not userid:
        raise HTTPException(status_code=400, detail="无法识别飞书身份")
    user = db.query(models.User).filter(models.User.feishu_userid == userid).first()
    if not user:
        user = models.User(
            feishu_userid=userid, nickname=nickname or f"飞书·{userid[-6:]}"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return schemas.TokenResponse(token=create_token(user.id), user=user)
