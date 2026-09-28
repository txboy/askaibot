import asyncio

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app import models, schemas
import app.routers.auth as auth_mod
from app.routers.auth import (
    feishu_callback,
    feishu_free_login,
    feishu_oauth,
    feishu_qrcode,
)


def _setting(**overrides):
    s = models.Setting()
    s.feishu_app_id = "cli_test"
    s.feishu_app_secret = "secret"
    s.feishu_redirect = "https://oabot.example.com"
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


def test_user_token_posts_and_parses(monkeypatch):
    fake = FakeHttp(
        FakeResp(
            {"code": 0, "access_token": "u-1", "open_id": "ou_x", "union_id": "on_x"}
        )
    )
    monkeypatch.setattr(auth_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    data = asyncio.run(auth_mod._feishu_user_token("cli", "sec", "code"))
    assert data["access_token"] == "u-1"
    url, kwargs = fake.posts[0]
    assert url == "https://open.feishu.cn/open-apis/authen/v1/access_token"
    assert kwargs["json"]["grant_type"] == "authorization_code"


def test_user_token_error_raises(monkeypatch):
    fake = FakeHttp(FakeResp({"code": 400, "msg": "bad code"}))
    monkeypatch.setattr(auth_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    with pytest_raises_http():
        asyncio.run(auth_mod._feishu_user_token("cli", "sec", "bad"))


def test_user_info_parses(monkeypatch):
    fake = FakeHttp(FakeResp({"code": 0, "data": {"name": "张三", "open_id": "ou_x"}}))
    monkeypatch.setattr(auth_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    info = asyncio.run(auth_mod._feishu_user_info("u-1"))
    assert info["name"] == "张三"
    assert info["open_id"] == "ou_x"
    url, kwargs = fake.gets[0]
    assert url == "https://open.feishu.cn/open-apis/authen/v1/user_info"


def test_qrcode_real_mode(monkeypatch):
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())
    monkeypatch.setattr(
        auth_mod,
        "_feishu_authorize_url",
        lambda s, state: (
            "https://open.feishu.cn/open-apis/authen/v1/authorize?state=" + state
        ),
    )
    r = feishu_qrcode(db=None)
    assert r["mode"] == "real"
    assert r["login_url"].startswith("https://open.feishu.cn")
    assert r["state"]


def test_qrcode_mock_mode(monkeypatch):
    monkeypatch.setattr(
        auth_mod,
        "get_setting",
        lambda db: _setting(feishu_app_id="", feishu_app_secret=""),
    )
    r = feishu_qrcode(db=None)
    assert r["mode"] == "mock"
    assert r["mock_code"].startswith("mock-fs-")
    assert r["login_url"].startswith("/api/auth/feishu/callback")


def test_qrcode_disabled_mode(monkeypatch):
    monkeypatch.setattr(
        auth_mod,
        "get_setting",
        lambda db: _setting(feishu_app_id="", feishu_app_secret="", debug_mode=0),
    )
    r = feishu_qrcode(db=None)
    assert r["mode"] == "disabled"


def test_oauth_redirects(monkeypatch):
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())
    monkeypatch.setattr(
        auth_mod,
        "_feishu_authorize_url",
        lambda s, state: (
            "https://open.feishu.cn/open-apis/authen/v1/authorize?state=" + state
        ),
    )
    resp = feishu_oauth(db=None, state="abc")
    assert resp.status_code in (301, 302, 307)
    assert "abc" in resp.headers["location"]


def test_callback_error_redirects(monkeypatch):
    monkeypatch.setattr(auth_mod, "get_setting", lambda db: _setting())

    async def fake_identity(a, s, code):
        raise HTTPException(status_code=400, detail="飞书登录失败：code=400")

    monkeypatch.setattr(auth_mod, "_feishu_identity", fake_identity)
    resp = asyncio.run(feishu_callback(code="abc", db=None))
    assert isinstance(resp, RedirectResponse)
    assert "/login?error=" in resp.headers["location"]


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

    async def fake_identity(a, s, code):
        return "on_union", "李四"

    monkeypatch.setattr(auth_mod, "_feishu_identity", fake_identity)
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-1")

    resp = asyncio.run(feishu_callback(code="abc", db=db))
    assert isinstance(resp, RedirectResponse)
    assert "/login?token=tok-1" in resp.headers["location"]
    assert (
        db.query(models.User).filter(models.User.feishu_userid == "on_union").count()
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
        lambda db: _setting(feishu_app_id="", feishu_app_secret=""),
    )
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-m")

    resp = asyncio.run(feishu_callback(code="mcode", db=db))
    assert isinstance(resp, RedirectResponse)
    assert "/login?token=tok-m" in resp.headers["location"]
    assert (
        db.query(models.User)
        .filter(models.User.feishu_userid == "mock-fs-mcode")
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

    async def fake_identity(a, s, code):
        return "on_free", "王五"

    monkeypatch.setattr(auth_mod, "_feishu_identity", fake_identity)
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-f")

    payload = schemas.FeishuCodeRequest(code="freecode")
    resp = asyncio.run(feishu_free_login(payload=payload, db=db))
    assert isinstance(resp, schemas.TokenResponse)
    assert resp.token == "tok-f"
    assert resp.user.nickname == "王五"
    assert (
        db.query(models.User).filter(models.User.feishu_userid == "on_free").count()
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
        lambda db: _setting(feishu_app_id="", feishu_app_secret=""),
    )
    monkeypatch.setattr(auth_mod, "create_token", lambda user_id: "tok-m")

    payload = schemas.FeishuCodeRequest(code="mm")
    resp = asyncio.run(feishu_free_login(payload=payload, db=db))
    assert isinstance(resp, schemas.TokenResponse)
    assert resp.token == "tok-m"
    assert (
        db.query(models.User).filter(models.User.feishu_userid == "mock-fs-mm").count()
        == 1
    )
    db.close()


def pytest_raises_http():
    import pytest

    return pytest.raises(HTTPException)
