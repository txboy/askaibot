import asyncio

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app import models
import app.controllers.frontend.auth as auth_mod
from app.controllers.frontend.auth import wecom_callback, wecom_oauth


class _Req:
    base_url = "http://testserver"


def _setting():
    s = models.Setting()
    s.wecom_corp_id = "wwtestcorp12345678"
    s.wecom_secret = "secret"
    s.wecom_agent_id = "1000001"
    s.wecom_redirect = "https://example.com"
    return s


def test_wecom_oauth_generates_state(monkeypatch):
    setting = _setting()
    captured = {}
    monkeypatch.setattr(auth_mod, "_wecom_is_real", lambda s: True)
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: setting)

    def fake_authorize(request, setting, state):
        captured["state"] = state
        return "https://open.weixin.qq.com/connect/oauth2/authorize?state=" + state

    monkeypatch.setattr(auth_mod, "_wecom_authorize_url", fake_authorize)
    resp = wecom_oauth(request=_Req(), db=None)
    assert resp.status_code in (301, 302, 307)
    assert captured["state"] and len(captured["state"]) > 10


def test_callback_real_mode_error_redirects_to_login(monkeypatch):
    setting = _setting()
    monkeypatch.setattr(auth_mod, "_wecom_is_real", lambda s: True)
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: setting)

    async def fake_exchange(setting, code):
        raise HTTPException(
            status_code=400, detail="企业微信用户信息获取失败：errcode=60020"
        )

    monkeypatch.setattr(auth_mod, "_wecom_exchange_userid", fake_exchange)
    resp = asyncio.run(wecom_callback(request=_Req(), code="abc", db=None))
    assert isinstance(resp, RedirectResponse)
    assert "/login?error=" in resp.headers["location"]
    assert "60020" in resp.headers["location"]


def test_callback_real_mode_empty_userid_redirects(monkeypatch):
    setting = _setting()
    monkeypatch.setattr(auth_mod, "_wecom_is_real", lambda s: True)
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: setting)

    async def fake_exchange(setting, code):
        return ""

    monkeypatch.setattr(auth_mod, "_wecom_exchange_userid", fake_exchange)
    resp = asyncio.run(wecom_callback(request=_Req(), code="abc", db=None))
    assert isinstance(resp, RedirectResponse)
    assert "/login?error=" in resp.headers["location"]


def test_callback_success_redirects_to_login_token(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import models as m
    from app.database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    setting = _setting()
    monkeypatch.setattr(auth_mod, "_wecom_is_real", lambda s: True)
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: setting)

    async def fake_exchange(setting, code):
        return "zhangsan"

    monkeypatch.setattr(auth_mod, "_wecom_exchange_userid", fake_exchange)
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-123")

    resp = asyncio.run(wecom_callback(request=_Req(), code="abc", db=db))
    db.close()
    assert isinstance(resp, RedirectResponse)
    assert "/login?token=tok-123" in resp.headers["location"]
    assert db.query(m.User).filter(m.User.wecom_userid == "zhangsan").count() == 1
