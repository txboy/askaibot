import asyncio
import base64
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.dingtalk_bot as dt_core
import app.controllers.webhook.dingtalk_bot as dt_router
import app.services.wecom_crypto as wc
from app import models
from app.database import Base

AES_KEY = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"


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
        name="钉钉客服",
        provider="dingtalk",
        corp_id="ding-app-key",
        secret="app-secret",
        agent_id="30001",
        token="token",
        aes_key=AES_KEY,
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


def _encrypt(xml: str, receive_id: str = "") -> str:
    return base64.b64encode(wc.encrypt_msg(xml, AES_KEY, receive_id)).decode()


def test_verify_returns_echostr(db):
    db.add(_bot())
    db.commit()
    plain = "socket-echo-123"
    enc_str = _encrypt(plain)
    sig = wc.signature("token", "123", "nonce", enc_str)

    resp = dt_router.verify(
        bot_id=1,
        signature=sig,
        timestamp="123",
        nonce="nonce",
        echostr=enc_str,
        db=db,
    )
    assert resp.status_code == 200
    assert resp.body == plain.encode()


def test_verify_bare_get_returns_success(db):
    """钉钉调试按钮发起的裸 GET（无签名/echostr 参数）应返回 200 success。"""
    db.add(_bot())
    db.commit()

    resp = dt_router.verify(
        bot_id=1,
        signature="",
        msg_signature="",
        timestamp="",
        nonce="",
        echostr="",
        db=db,
    )
    assert resp.status_code == 200
    assert resp.body == b"success"


def test_verify_bad_signature_raises(db):
    db.add(_bot())
    db.commit()
    enc_str = _encrypt("echo")
    with pytest.raises(Exception):
        dt_router.verify(
            bot_id=1,
            signature="bad",
            timestamp="123",
            nonce="nonce",
            echostr=enc_str,
            db=db,
        )


def test_verify_missing_bot_raises(db):
    with pytest.raises(Exception):
        dt_router.verify(
            bot_id=999,
            signature="s",
            timestamp="1",
            nonce="2",
            echostr="x",
            db=db,
        )


def test_receive_text_flow(db, monkeypatch):
    bot = _bot()
    db.add(bot)
    db.commit()

    xml = "<xml><ToUserName>corpId</ToUserName><FromUserName>manager01</FromUserName><MsgType>text</MsgType><Content>在吗？</Content></xml>"
    enc_str = _encrypt(xml)
    sig = wc.signature("token", "123", "nonce", enc_str)
    body = json_bytes({"encrypt": enc_str})

    replied = {}
    sent = []

    async def fake_reply(db, conversation, bot):
        replied["conv"] = conversation.id
        return "在的，请讲"

    async def fake_send(userid, content, agent_id, app_key, app_secret):
        sent.append((userid, content))

    monkeypatch.setattr(dt_router, "generate_reply", fake_reply)
    monkeypatch.setattr(dt_core, "send_text", fake_send)

    class FakeRequest:
        async def body(self):
            return body

    async def run():
        return await dt_router.receive(
            bot_id=1,
            request=FakeRequest(),
            signature=sig,
            timestamp="123",
            nonce="nonce",
            db=db,
        )

    resp = asyncio.run(run())
    assert resp.status_code == 200

    user = (
        db.query(models.User).filter(models.User.dingtalk_userid == "manager01").first()
    )
    assert user is not None
    conv = db.query(models.Conversation).filter(models.Conversation.bot_id == 1).first()
    assert conv is not None
    msgs = (
        db.query(models.Message).filter(models.Message.conversation_id == conv.id).all()
    )
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].content == "在吗？"
    assert msgs[1].content == "在的，请讲"
    assert sent == [("manager01", "在的，请讲")]


def test_receive_non_text_replies_unsupported(db, monkeypatch):
    db.add(_bot())
    db.commit()

    xml = "<xml><ToUserName>corpId</ToUserName><FromUserName>userA</FromUserName><MsgType>image</MsgType><MediaId>M1</MediaId></xml>"
    enc_str = _encrypt(xml)
    sig = wc.signature("token", "123", "nonce", enc_str)
    body = json_bytes({"encrypt": enc_str})

    sent = []

    async def fake_send(userid, content, agent_id, app_key, app_secret):
        sent.append((userid, content))

    monkeypatch.setattr(dt_core, "send_text", fake_send)

    class FakeRequest:
        async def body(self):
            return body

    async def run():
        return await dt_router.receive(
            bot_id=1,
            request=FakeRequest(),
            signature=sig,
            timestamp="123",
            nonce="nonce",
            db=db,
        )

    asyncio.run(run())
    assert sent and sent[0][1] == "暂不支持该类型消息，请发送文字。"

    conv = db.query(models.Conversation).filter(models.Conversation.bot_id == 1).first()
    msgs = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conv.id)
        .order_by(models.Message.id.asc())
        .all()
    )
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].content == "[image消息]"


def test_receive_bad_signature_raises(db):
    db.add(_bot())
    db.commit()

    class FakeRequest:
        async def body(self):
            return json_bytes({"encrypt": "xx"})

    with pytest.raises(Exception):
        asyncio.run(
            dt_router.receive(
                bot_id=1,
                request=FakeRequest(),
                signature="bad",
                timestamp="1",
                nonce="2",
                db=db,
            )
        )


def test_receive_check_url_returns_encrypted_success(db):
    db.add(_bot())
    db.commit()
    echo = '{"EventType":"check_url"}'
    enc_str = _encrypt(echo)
    sig = wc.signature("token", "123", "nonce", enc_str)
    body = json_bytes({"encrypt": enc_str})

    class FakeRequest:
        async def body(self):
            return body

    async def run():
        return await dt_router.receive(
            bot_id=1,
            request=FakeRequest(),
            signature=sig,
            timestamp="123",
            nonce="nonce",
            db=db,
        )

    resp = asyncio.run(run())
    assert resp.status_code == 200
    assert resp.media_type == "application/json"
    payload = json.loads(resp.body)
    assert set(payload) == {"msg_signature", "timeStamp", "nonce", "encrypt"}
    assert payload["timeStamp"] == "123"
    assert payload["nonce"] == "nonce"
    assert payload["msg_signature"] == wc.signature(
        "token", "123", "nonce", payload["encrypt"]
    )
    plain = wc.decrypt_msg(
        base64.b64decode(payload["encrypt"]), AES_KEY, "", check_receive_id=False
    )
    assert plain == "success"


def test_receive_non_message_returns_success(db):
    db.add(_bot())
    db.commit()
    echo = "owner-verify-string"
    enc_str = _encrypt(echo)
    sig = wc.signature("token", "123", "nonce", enc_str)
    body = json_bytes({"encrypt": enc_str})

    class FakeRequest:
        async def body(self):
            return body

    async def run():
        return await dt_router.receive(
            bot_id=1,
            request=FakeRequest(),
            signature=sig,
            timestamp="123",
            nonce="nonce",
            db=db,
        )

    resp = asyncio.run(run())
    assert resp.status_code == 200
    assert resp.body == b"success"


def test_parse_json_message():
    payload = json.dumps(
        {
            "msgtype": "text",
            "text": {"content": "你好，钉钉"},
            "senderStaffId": "user001",
            "senderNick": "张三",
            "robotCode": "ding-app-key",
        }
    )
    msg = dt_router._parse_message(payload)
    assert msg["FromUserName"] == "user001"
    assert msg["MsgType"] == "text"
    assert msg["Content"] == "你好，钉钉"
    assert msg["ToUserName"] == "ding-app-key"


def test_parse_xml_message():
    xml = "<xml><FromUserName>w001</FromUserName><MsgType>text</MsgType><Content>hi</Content></xml>"
    msg = dt_router._parse_message(xml)
    assert msg["FromUserName"] == "w001"
    assert msg["Content"] == "hi"


def test_parse_message_non_parseable_raises():
    with pytest.raises(Exception):
        dt_router._parse_message("not xml not json")


def test_get_access_token_caches(monkeypatch):
    fake = FakeHttp(FakeResp({"errcode": 0, "access_token": "DT", "expires_in": 7200}))
    monkeypatch.setattr(dt_core.httpx, "AsyncClient", lambda *a, **k: fake)
    assert asyncio.run(dt_core.get_access_token("ak", "as")) == "DT"
    assert asyncio.run(dt_core.get_access_token("ak", "as")) == "DT"
    assert len(fake.gets) == 1


def test_get_access_token_error_raises(monkeypatch):
    monkeypatch.setattr(
        dt_core.httpx,
        "AsyncClient",
        lambda *a, **k: FakeHttp(FakeResp({"errcode": 40001, "errmsg": "invalid"})),
    )
    with pytest.raises(RuntimeError):
        asyncio.run(dt_core.get_access_token("ak2", "as2"))


def test_send_text_posts_correct_payload(monkeypatch):
    fake = FakeHttp(FakeResp({"errcode": 0}))
    monkeypatch.setattr(dt_core.httpx, "AsyncClient", lambda *a, **k: fake)

    async def fake_token(app_key, app_secret):
        return "TOKEN"

    monkeypatch.setattr(dt_core, "get_access_token", fake_token)

    asyncio.run(dt_core.send_text("user001", "你好", "30001", "ak", "as"))
    assert len(fake.posts) == 1
    url, kwargs = fake.posts[0]
    assert (
        url == "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"
    )
    assert kwargs["params"] == {"access_token": "TOKEN"}
    assert kwargs["json"]["agent_id"] == 30001
    assert kwargs["json"]["userid_list"] == "user001"
    assert "你好" in kwargs["json"]["msg"]


def test_send_text_error_raises(monkeypatch):
    fake = FakeHttp(FakeResp({"errcode": 400, "errmsg": "bad"}))
    monkeypatch.setattr(dt_core.httpx, "AsyncClient", lambda *a, **k: fake)

    async def fake_token(app_key, app_secret):
        return "TOKEN"

    monkeypatch.setattr(dt_core, "get_access_token", fake_token)

    with pytest.raises(RuntimeError):
        asyncio.run(dt_core.send_text("u", "hi", "30001", "ak", "as"))


def json_bytes(d):
    import json

    return json.dumps(d).encode()
