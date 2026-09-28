import asyncio

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app import models, schemas
import app.controllers.frontend.auth as auth_mod
from app.controllers.frontend.auth import (
    dingtalk_callback,
    dingtalk_free_login,
    dingtalk_oauth,
    dingtalk_qrcode,
)


def _setting(**overrides):
    s = models.Setting()
    s.dingtalk_app_key = "ding-key"
    s.dingtalk_app_secret = "ding-secret"
    s.dingtalk_agent_id = "30001"
    s.dingtalk_redirect = "https://oabot.example.com"
    s.debug_mode = 1
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


class FakeHttp:
    def __init__(self, data):
        self.posts = []
        self.gets = []
        self._data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return self._data

    async def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return self._data


class FakeResp:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


def test_user_token_parses_access_token(monkeypatch):
    fake = FakeHttp(FakeResp({"accessToken": "AT-123"}))
    monkeypatch.setattr(auth_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    token = asyncio.run(auth_mod._dingtalk_user_token("ck", "cs", "code"))
    assert token == "AT-123"
    url, kwargs = fake.posts[0]
    assert url == "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
    assert kwargs["json"]["clientId"] == "ck"
    assert kwargs["json"]["grantType"] == "authorization_code"


def test_user_token_missing_raises(monkeypatch):
    fake = FakeHttp(FakeResp({"message": "bad code"}))
    monkeypatch.setattr(auth_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    with pytest_raises_http():
        asyncio.run(auth_mod._dingtalk_user_token("ck", "cs", "bad"))


def test_user_info_parses_user_id(monkeypatch):
    fake = FakeHttp(FakeResp({"userId": "u1", "nick": "张三"}))
    monkeypatch.setattr(auth_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    info = asyncio.run(auth_mod._dingtalk_user_info("AT"))
    assert info["userId"] == "u1"
    assert info["nick"] == "张三"
    url, kwargs = fake.gets[0]
    assert url == "https://api.dingtalk.com/v1.0/contact/users/me"
    assert kwargs["headers"]["x-acs-dingtalk-access-token"] == "AT"


def test_user_info_missing_user_id_raises(monkeypatch):
    fake = FakeHttp(FakeResp({"message": "no user"}))
    monkeypatch.setattr(auth_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    with pytest_raises_http():
        asyncio.run(auth_mod._dingtalk_user_info("AT"))


def test_qrcode_real_mode(monkeypatch):
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())
    monkeypatch.setattr(
        auth_mod,
        "_dingtalk_authorize_url",
        lambda s, state: "https://login.dingtalk.com/oauth2/auth?state=" + state,
    )
    r = dingtalk_qrcode(db=None)
    assert r["mode"] == "real"
    assert r["login_url"].startswith("https://login.dingtalk.com/oauth2/auth")
    assert r["state"]


def test_qrcode_mock_mode(monkeypatch):
    monkeypatch.setattr(
        auth_mod,
        "get_setting",
        lambda db: _setting(dingtalk_app_key="", dingtalk_app_secret=""),
    )
    r = dingtalk_qrcode(db=None)
    assert r["mode"] == "mock"
    assert r["mock_code"].startswith("mock-dd-")
    assert r["login_url"].startswith("/api/auth/dingtalk/callback")


def test_qrcode_disabled_mode(monkeypatch):
    monkeypatch.setattr(
        auth_mod,
        "get_setting",
        lambda db: _setting(dingtalk_app_key="", dingtalk_app_secret="", debug_mode=0),
    )
    r = dingtalk_qrcode(db=None)
    assert r["mode"] == "disabled"


def test_oauth_redirects(monkeypatch):
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())
    monkeypatch.setattr(
        auth_mod,
        "_dingtalk_authorize_url",
        lambda s, state: "https://login.dingtalk.com/oauth2/auth?state=" + state,
    )
    resp = dingtalk_oauth(db=None, state="abc")
    assert resp.status_code in (301, 302, 307)
    assert "abc" in resp.headers["location"]


def test_callback_error_redirects_to_login(monkeypatch):
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())

    async def fake_token(client_id, client_secret, code):
        raise HTTPException(status_code=400, detail="钉钉登录失败：bad code")

    monkeypatch.setattr(auth_mod, "_dingtalk_user_token", fake_token)
    resp = asyncio.run(dingtalk_callback(code="abc", db=None))
    assert isinstance(resp, RedirectResponse)
    assert "/login?error=" in resp.headers["location"]
    assert "bad" in resp.headers["location"]


def test_callback_success_creates_user(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())

    async def fake_token(client_id, client_secret, code):
        return "AT"

    async def fake_info(token):
        return {"userId": "dt-user", "nick": "李四"}

    monkeypatch.setattr(auth_mod, "_dingtalk_user_token", fake_token)
    monkeypatch.setattr(auth_mod, "_dingtalk_user_info", fake_info)
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-456")

    resp = asyncio.run(dingtalk_callback(code="abc", db=db))
    assert isinstance(resp, RedirectResponse)
    assert "/login?token=tok-456" in resp.headers["location"]
    assert (
        db.query(models.User).filter(models.User.dingtalk_userid == "dt-user").count()
        == 1
    )
    db.close()


def test_callback_mock_creates_user(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    monkeypatch.setattr(
        auth_mod,
        "get_setting",
        lambda db: _setting(dingtalk_app_key="", dingtalk_app_secret=""),
    )
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-mock")

    resp = asyncio.run(dingtalk_callback(code="mcode", db=db))
    assert isinstance(resp, RedirectResponse)
    assert "/login?token=tok-mock" in resp.headers["location"]
    assert (
        db.query(models.User)
        .filter(models.User.dingtalk_userid == "mock-dd-mcode")
        .count()
        == 1
    )
    db.close()


def test_free_login_real_returns_token(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())

    async def fake_token(client_id, client_secret, code):
        return "AT"

    async def fake_info(token):
        return {"userId": "free-u", "nick": "王五"}

    monkeypatch.setattr(auth_mod, "_dingtalk_user_token", fake_token)
    monkeypatch.setattr(auth_mod, "_dingtalk_user_info", fake_info)
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-free")

    payload = schemas.DingtalkCodeRequest(code="freecode")
    resp = asyncio.run(dingtalk_free_login(payload=payload, db=db))
    assert isinstance(resp, schemas.TokenResponse)
    assert resp.token == "tok-free"
    assert resp.user.nickname == "王五"
    assert (
        db.query(models.User).filter(models.User.dingtalk_userid == "free-u").count()
        == 1
    )
    db.close()


def test_free_login_mock_returns_token(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    monkeypatch.setattr(
        auth_mod,
        "get_setting",
        lambda db: _setting(dingtalk_app_key="", dingtalk_app_secret=""),
    )
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-m")

    payload = schemas.DingtalkCodeRequest(code="mm")
    resp = asyncio.run(dingtalk_free_login(payload=payload, db=db))
    assert isinstance(resp, schemas.TokenResponse)
    assert resp.token == "tok-m"
    assert (
        db.query(models.User)
        .filter(models.User.dingtalk_userid == "mock-dd-mm")
        .count()
        == 1
    )
    db.close()


def pytest_raises_http():
    import pytest

    return pytest.raises(HTTPException)
