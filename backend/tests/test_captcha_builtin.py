from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, schemas
import app.captcha as captcha_mod
import app.routers.auth as auth_mod
from app.database import Base


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _setting(db, **kw):
    setting = models.Setting(id=1, **kw)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@pytest.fixture(autouse=True)
def _clean():
    auth_mod._sms_codes.clear()
    captcha_mod._builtin_captchas.clear()
    yield


def test_build_challenge_builtin_returns_image():
    setting = models.Setting(id=1, sms_captcha_provider="builtin")
    out = captcha_mod.build_challenge(setting)
    assert out["type"] == "image"
    assert out["captcha_id"]
    assert out["image_base64"]


def test_get_captcha_endpoint_returns_challenge():
    db = _db()
    _setting(db, sms_captcha_enabled=1, sms_captcha_provider="builtin", debug_mode=1)
    out = auth_mod.get_captcha(db=db)
    assert out["type"] == "image"
    assert out["captcha_id"]


def test_sms_send_no_captcha_when_disabled():
    db = _db()
    _setting(db, sms_captcha_enabled=0, debug_mode=1)
    res = auth_mod.sms_send(payload=schemas.SMSRequest(phone="13800000001"), db=db)
    assert res["debug_code"]


def test_sms_send_requires_captcha():
    db = _db()
    _setting(db, sms_captcha_enabled=1, debug_mode=1)
    with pytest.raises(HTTPException) as exc:
        auth_mod.sms_send(payload=schemas.SMSRequest(phone="13800000002"), db=db)
    assert exc.value.status_code == 400


def test_sms_send_wrong_captcha_400():
    db = _db()
    _setting(db, sms_captcha_enabled=1, debug_mode=1)
    challenge = captcha_mod.build_challenge(models.Setting(id=1))
    payload = schemas.SMSRequest(
        phone="13800000003",
        captcha_id=challenge["captcha_id"],
        captcha="XXXX",
    )
    with pytest.raises(HTTPException) as exc:
        auth_mod.sms_send(payload=payload, db=db)
    assert exc.value.status_code == 400


def test_sms_send_correct_captcha_succeeds_case_insensitive():
    db = _db()
    _setting(db, sms_captcha_enabled=1, debug_mode=1)
    challenge = captcha_mod.build_challenge(models.Setting(id=1))
    code = captcha_mod._builtin_captchas[challenge["captcha_id"]]["code"]
    res = auth_mod.sms_send(
        payload=schemas.SMSRequest(
            phone="13800000004",
            captcha_id=challenge["captcha_id"],
            captcha=code.upper(),
        ),
        db=db,
    )
    assert res["debug_code"]


def test_sms_captcha_one_time_use():
    db = _db()
    _setting(db, sms_captcha_enabled=1, debug_mode=1)
    challenge = captcha_mod.build_challenge(models.Setting(id=1))
    code = captcha_mod._builtin_captchas[challenge["captcha_id"]]["code"]
    payload = schemas.SMSRequest(
        phone="13800000005",
        captcha_id=challenge["captcha_id"],
        captcha=code,
    )
    assert auth_mod.sms_send(payload=payload, db=db)["debug_code"]
    with pytest.raises(HTTPException) as exc:
        auth_mod.sms_send(payload=payload, db=db)
    assert exc.value.status_code == 400


def test_sms_send_cooldown_429():
    db = _db()
    _setting(db, sms_captcha_enabled=0, debug_mode=1, sms_cooldown=60)
    auth_mod._sms_codes["13800000006"] = {
        "code": "123456",
        "expires": datetime.now() + timedelta(minutes=5),
        "sent_at": datetime.now(),
    }
    with pytest.raises(HTTPException) as exc:
        auth_mod.sms_send(payload=schemas.SMSRequest(phone="13800000006"), db=db)
    assert exc.value.status_code == 429


def test_sms_send_cooldown_expired_allows():
    db = _db()
    _setting(db, sms_captcha_enabled=0, debug_mode=1, sms_cooldown=60)
    auth_mod._sms_codes["13800000007"] = {
        "code": "123456",
        "expires": datetime.now() + timedelta(minutes=5),
        "sent_at": datetime.now() - timedelta(seconds=70),
    }
    res = auth_mod.sms_send(payload=schemas.SMSRequest(phone="13800000007"), db=db)
    assert res["debug_code"]


def test_verify_resets_cooldown_for_resend():
    db = _db()
    _setting(db, sms_captcha_enabled=0, debug_mode=1)
    phone = "13800000008"
    auth_mod._sms_codes[phone] = {
        "code": "123456",
        "expires": datetime.now() + timedelta(minutes=5),
        "sent_at": datetime.now(),
    }
    token_resp = auth_mod.sms_verify(
        payload=schemas.SMSVerifyRequest(phone=phone, code="123456"), db=db
    )
    assert token_resp.token
    res = auth_mod.sms_send(payload=schemas.SMSRequest(phone=phone), db=db)
    assert res["debug_code"]
