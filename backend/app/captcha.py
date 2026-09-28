"""可插拔短信验证码：builtin(图形) / geetest / tencent / aliyun。

所有厂商校验函数均为独立可打桩函数，便于单元测试。
"""

import base64
import hashlib
import hmac
import io
import random
import uuid
from datetime import datetime, timedelta

import httpx

BUILTIN = "builtin"
GEETEST = "geetest"
TENCENT = "tencent"
ALIYUN = "aliyun"

_builtin_captchas: dict[str, dict] = {}


def _now():
    return datetime.now()


def build_challenge(setting) -> dict:
    """按配置返回前端初始化所需信息。"""
    provider = (setting.sms_captcha_provider or BUILTIN).lower()
    if provider == GEETEST:
        return {"type": GEETEST, "captcha_id": setting.geetest_captcha_id or ""}
    if provider == TENCENT:
        return {"type": TENCENT, "app_id": setting.tencent_captcha_app_id or ""}
    if provider == ALIYUN:
        return {
            "type": ALIYUN,
            "scene_id": setting.aliyun_captcha_scene_id or "",
        }
    captcha_id, code = _new_builtin_captcha()
    return {
        "type": "image",
        "captcha_id": captcha_id,
        "image_base64": _render_image(code),
    }


def verify(setting, payload) -> bool:
    """按配置校验验证码。payload 为 SMSRequest（含各厂商字段）。"""
    provider = (setting.sms_captcha_provider or BUILTIN).lower()
    if provider == GEETEST:
        return _verify_geetest(setting, payload)
    if provider == TENCENT:
        return _verify_tencent(setting, payload)
    if provider == ALIYUN:
        return _verify_aliyun(setting, payload)
    return _verify_builtin(payload)


# ---------------- builtin 图形验证码 ----------------

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/verdana.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/courbd.ttf",
    "C:/Windows/Fonts/msyhbd.ttc",
]


def _load_font(size: int):
    from PIL import ImageFont

    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _new_builtin_captcha():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(random.choices(chars, k=4))
    captcha_id = uuid.uuid4().hex
    _builtin_captchas[captcha_id] = {
        "code": code.lower(),
        "expires": _now() + timedelta(minutes=5),
    }
    return captcha_id, code


def _render_image(code: str) -> str:
    from PIL import Image, ImageDraw

    width, height = 140, 46
    img = Image.new("RGB", (width, height), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    font = _load_font(30)

    # 干扰线
    for _ in range(8):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(
            (x1, y1, x2, y2),
            fill=(
                random.randint(120, 220),
                random.randint(120, 220),
                random.randint(120, 220),
            ),
            width=1,
        )

    # 字符，逐个随机旋转/倾斜粘贴
    char_width = width // (len(code) + 1)
    for i, ch in enumerate(code):
        layer = Image.new("RGBA", (char_width + 10, 40), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        color = (
            random.randint(20, 120),
            random.randint(20, 120),
            random.randint(20, 120),
        )
        ld.text((4, -4), ch, font=font, fill=color)
        layer = layer.rotate(random.uniform(-28, 28), expand=1)
        x = (i + 1) * char_width - 10
        y = random.randint(0, 8)
        img.paste(layer, (x, y), layer)

    # 噪点
    for _ in range(120):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=(
                random.randint(0, 200),
                random.randint(0, 200),
                random.randint(0, 200),
            ),
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _verify_builtin(payload) -> bool:
    captcha_id = getattr(payload, "captcha_id", "") or ""
    captcha = (getattr(payload, "captcha", "") or "").strip().lower()
    entry = _builtin_captchas.pop(captcha_id, None)
    if not entry or entry["expires"] < _now():
        return False
    return entry["code"] == captcha


# ---------------- geetest ----------------


def _verify_geetest(setting, payload) -> bool:
    captcha_id = setting.geetest_captcha_id or ""
    captcha_key = setting.geetest_captcha_key or ""
    lot_number = getattr(payload, "lot_number", "") or ""
    captcha_output = getattr(payload, "captcha_output", "") or ""
    pass_token = getattr(payload, "pass_token", "") or ""
    gen_time = str(getattr(payload, "gen_time", "") or "")
    if not captcha_id or not captcha_key or not lot_number:
        return False
    sign_token = hmac.new(
        captcha_key.encode("utf-8"), lot_number.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    try:
        resp = httpx.post(
            "http://gcaptcha4.geetest.com/validate",
            params={"captcha_id": captcha_id},
            data={
                "lot_number": lot_number,
                "captcha_output": captcha_output,
                "pass_token": pass_token,
                "gen_time": gen_time,
                "sign_token": sign_token,
            },
            timeout=10,
        )
        data = resp.json()
    except Exception:
        return False
    return data.get("result") == "success"


# ---------------- tencent (经典 ssl.captcha.qq.com) ----------------


def _verify_tencent(setting, payload) -> bool:
    app_id = setting.tencent_captcha_app_id or ""
    app_secret_key = setting.tencent_captcha_app_secret_key or ""
    ticket = getattr(payload, "ticket", "") or ""
    randstr = getattr(payload, "randstr", "") or ""
    if not app_id or not app_secret_key or not ticket:
        return False
    return _tencent_request(app_id, app_secret_key, ticket, randstr)


def _tencent_request(
    app_id: str, app_secret_key: str, ticket: str, randstr: str
) -> bool:
    try:
        resp = httpx.post(
            "https://ssl.captcha.qq.com/cgi-bin/Response",
            params={"aid": app_id},
            data={
                "AppSecretKey": app_secret_key,
                "Randstr": randstr,
                "Ticket": ticket,
                "CaptchaType": 1,
            },
            timeout=10,
        )
        text = resp.text.strip().strip('"')
        return text == "0"
    except Exception:
        return False


# ---------------- aliyun 验证码2.0 ----------------


def _verify_aliyun(setting, payload) -> bool:
    captcha_verify_param = getattr(payload, "captcha_verify_param", "") or ""
    return _aliyun_request(
        setting.aliyun_captcha_access_key_id or "",
        setting.aliyun_captcha_access_key_secret or "",
        setting.aliyun_captcha_scene_id or "",
        captcha_verify_param,
    )


def _aliyun_request(
    access_key_id, access_key_secret, scene_id, captcha_verify_param
) -> bool:
    if not access_key_id or not access_key_secret or not captcha_verify_param:
        return False
    try:
        from alibabacloud_captcha20230305 import client as ac
        from alibabacloud_captcha20230305 import models as am
        from alibabacloud_tea_openapi import models as om

        config = om.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="captcha.cn-shanghai.aliyuncs.com",
        )
        client = ac.Client(config)
        req = am.VerifyIntelligentCaptchaRequest(
            captcha_verify_param=captcha_verify_param,
            scene_id=scene_id,
        )
        resp = client.verify_intelligent_captcha(req)
        result = getattr(resp.body, "result", None)
        return bool(result and (result.verify_result or result.verify_code == "200"))
    except Exception:
        return False
