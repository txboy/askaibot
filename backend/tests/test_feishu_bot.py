import asyncio
import json

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.feishu_bot as fs_core
import app.services.feishu_crypto as fc
import app.controllers.webhook.feishu_bot as fs_router
from app import models
from app.database import Base

ENC_KEY = "my-feishu-encrypt-key"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _bot(**overrides):
    data = dict(
        id=1,
        name="飞书客服",
        provider="feishu",
        corp_id="cli_appid",
        secret="app-secret",
        agent_id="",
        token="verify-token",
        aes_key="",
        kb_ids="",
        web_search=0,
        enabled=1,
    )
    data.update(overrides)
    return models.WecomBot(**data)


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


class FakeRequest:
    def __init__(self, body):
        self._body = body

    async def body(self):
        return self._body


def _challenge_body():
    return json.dumps(
        {"challenge": "abc123", "token": "verify-token", "type": "url_verification"}
    ).encode()


def test_url_verification_returns_challenge(db):
    db.add(_bot())
    db.commit()
    resp = asyncio.run(
        fs_router.receive(1, FakeRequest(_challenge_body()), BackgroundTasks(), db=db)
    )
    assert resp.status_code == 200
    assert json.loads(resp.body)["challenge"] == "abc123"


def test_decrypt_official_feishu_vector():
    # 官方文档示例：encrypt="P37w+VZImNgPEO1RBhJ6RtKl7n6zymIbEG1pReEzghk=", key="test key" -> "hello world"
    assert (
        fc.decrypt("test key", "P37w+VZImNgPEO1RBhJ6RtKl7n6zymIbEG1pReEzghk=")
        == "hello world"
    )


def test_url_verification_token_mismatch_raises(db):
    db.add(_bot())
    db.commit()
    body = json.dumps(
        {"challenge": "abc", "token": "wrong", "type": "url_verification"}
    ).encode()
    with pytest.raises(Exception):
        asyncio.run(fs_router.receive(1, FakeRequest(body), BackgroundTasks(), db=db))


def test_encrypted_url_verification_returns_encrypted_challenge(db):
    db.add(_bot(aes_key=ENC_KEY))
    db.commit()
    plain = json.dumps(
        {"challenge": "xyz", "token": "verify-token", "type": "url_verification"}
    )
    body = json.dumps({"encrypt": fc.encrypt(ENC_KEY, plain)}).encode()
    resp = asyncio.run(
        fs_router.receive(1, FakeRequest(body), BackgroundTasks(), db=db)
    )
    assert resp.status_code == 200
    resp_data = json.loads(resp.body)
    assert "encrypt" in resp_data
    assert fc.decrypt(ENC_KEY, resp_data["encrypt"]) == plain


def test_receive_event_replies(db, monkeypatch):
    bot = _bot()
    db.add(bot)
    db.commit()

    event = {
        "schema": "2.0",
        "header": {
            "event_type": "im.message.receive_v1",
            "event_id": "e1",
            "token": "verify-token",
            "app_id": "cli_appid",
        },
        "event": {
            "sender": {
                "sender_id": {
                    "open_id": "ou_123",
                    "union_id": "on_123",
                    "user_id": "u123",
                },
                "sender_type": "user",
            },
            "message": {
                "message_id": "om_1",
                "chat_id": "oc_1",
                "chat_type": "p2p",
                "message_type": "text",
                "content": json.dumps({"text": "在吗？"}),
            },
        },
    }
    body = json.dumps(event).encode()

    replied = {}
    sent = []

    async def fake_reply(db, conversation, bot):
        replied["conv"] = conversation.id
        return "在的，请讲"

    async def fake_send(open_id, content, app_id, app_secret):
        sent.append((open_id, content))

    monkeypatch.setattr(fs_router, "generate_reply", fake_reply)
    monkeypatch.setattr(fs_core, "send_text", fake_send)
    monkeypatch.setattr(fs_router, "SessionLocal", sessionmaker(bind=db.get_bind()))

    bt = BackgroundTasks()
    resp = asyncio.run(fs_router.receive(1, FakeRequest(body), bt, db=db))
    assert resp.status_code == 200
    asyncio.run(bt())

    user = db.query(models.User).filter(models.User.feishu_userid == "ou_123").first()
    assert user is not None
    conv = db.query(models.Conversation).filter(models.Conversation.bot_id == 1).first()
    assert conv is not None
    msgs = (
        db.query(models.Message).filter(models.Message.conversation_id == conv.id).all()
    )
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].content == "在吗？"
    assert msgs[1].content == "在的，请讲"
    assert sent == [("ou_123", "在的，请讲")]


def test_receive_non_text_replies_unsupported(db, monkeypatch):
    db.add(_bot())
    db.commit()
    event = {
        "event": {
            "sender": {"sender_id": {"open_id": "ou_9", "union_id": "on_9"}},
            "message": {
                "message_type": "image",
                "content": json.dumps({"image_key": "img_k"}),
            },
        }
    }
    body = json.dumps(event).encode()
    sent = []

    async def fake_send(open_id, content, app_id, app_secret):
        sent.append((open_id, content))

    monkeypatch.setattr(fs_core, "send_text", fake_send)
    monkeypatch.setattr(fs_router, "SessionLocal", sessionmaker(bind=db.get_bind()))
    bt = BackgroundTasks()
    asyncio.run(fs_router.receive(1, FakeRequest(body), bt, db=db))
    asyncio.run(bt())
    assert sent and sent[0][1] == "暂不支持该类型消息，请发送文字。"


def test_receive_missing_bot_raises(db):
    body = json.dumps({"challenge": "x"}).encode()
    with pytest.raises(Exception):
        asyncio.run(fs_router.receive(999, FakeRequest(body), BackgroundTasks(), db=db))


def test_receive_duplicate_event_skips_processing(db, monkeypatch):
    db.add(_bot())
    db.commit()
    monkeypatch.setattr(fs_router, "SessionLocal", sessionmaker(bind=db.get_bind()))

    event = {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1", "event_id": "dup1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_dup"}},
            "message": {
                "message_type": "text",
                "content": json.dumps({"text": "hi"}),
            },
        },
    }
    body = json.dumps(event).encode()
    sent = []

    async def fake_send(open_id, content, app_id, app_secret):
        sent.append((open_id, content))

    async def fake_reply(db, conversation, bot):
        return "ok"

    monkeypatch.setattr(fs_core, "send_text", fake_send)
    monkeypatch.setattr(fs_router, "generate_reply", fake_reply)

    bt1 = BackgroundTasks()
    asyncio.run(fs_router.receive(1, FakeRequest(body), bt1, db=db))
    asyncio.run(bt1())
    assert len(sent) == 1

    bt2 = BackgroundTasks()
    asyncio.run(fs_router.receive(1, FakeRequest(body), bt2, db=db))
    asyncio.run(bt2())
    assert len(sent) == 1
    assert db.query(models.BotEvent).count() == 1


def test_get_access_token_caches(monkeypatch):
    fake = FakeHttp(FakeResp({"code": 0, "tenant_access_token": "T", "expire": 7200}))
    monkeypatch.setattr(fs_core.httpx, "AsyncClient", lambda *a, **k: fake)
    assert asyncio.run(fs_core.get_access_token("cli", "sec")) == "T"
    assert asyncio.run(fs_core.get_access_token("cli", "sec")) == "T"
    assert len(fake.posts) == 1


def test_get_access_token_error_raises(monkeypatch):
    monkeypatch.setattr(
        fs_core.httpx,
        "AsyncClient",
        lambda *a, **k: FakeHttp(FakeResp({"code": 10002, "msg": "bad"})),
    )
    with pytest.raises(RuntimeError):
        asyncio.run(fs_core.get_access_token("cli_err", "sec_err"))


def test_send_text_posts_correct_payload(monkeypatch):
    fake = FakeHttp(FakeResp({"code": 0}))
    monkeypatch.setattr(fs_core.httpx, "AsyncClient", lambda *a, **k: fake)

    async def fake_token(app_id, app_secret):
        return "TOKEN"

    monkeypatch.setattr(fs_core, "get_access_token", fake_token)

    asyncio.run(fs_core.send_text("ou_u", "你好", "cli", "sec"))
    assert len(fake.posts) == 1
    url, kwargs = fake.posts[0]
    assert url == "https://open.feishu.cn/open-apis/im/v1/messages"
    assert kwargs["params"] == {"receive_id_type": "open_id"}
    assert kwargs["headers"]["Authorization"] == "Bearer TOKEN"
    assert kwargs["json"]["receive_id"] == "ou_u"
    assert kwargs["json"]["msg_type"] == "text"
    assert "你好" in kwargs["json"]["content"]
