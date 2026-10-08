import asyncio
import base64
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.webhook.wecom_bot as wecom_router
import app.services.kb as kb_mod
import app.services.wecom_bot as bot_core
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
        name="客服机器人",
        corp_id="corp123",
        secret="secret",
        agent_id="1000002",
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


def test_get_access_token_caches(monkeypatch):
    class TokClient(FakeHttp):
        pass

    fake = TokClient(FakeResp({"errcode": 0, "access_token": "T", "expires_in": 7200}))
    monkeypatch.setattr(bot_core.httpx, "AsyncClient", lambda *a, **k: fake)
    assert asyncio.run(bot_core.get_access_token("c", "s")) == "T"
    assert asyncio.run(bot_core.get_access_token("c", "s")) == "T"
    assert len(fake.gets) == 1


def test_get_access_token_error_raises(monkeypatch):
    class ErrClient(FakeHttp):
        pass

    monkeypatch.setattr(
        bot_core.httpx,
        "AsyncClient",
        lambda *a, **k: ErrClient(FakeResp({"errcode": 41001, "errmsg": "invalid"})),
    )
    with pytest.raises(RuntimeError):
        asyncio.run(bot_core.get_access_token("c2", "s2"))


def test_generate_reply_uses_endpoint_and_returns_content(monkeypatch, db):
    ep = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    bot = _bot(endpoint_id=1, model="gpt-test")
    user = models.User(id=1, nickname="u")
    conversation = models.Conversation(id=1, user_id=1, bot_id=1, title="c")
    db.add_all([ep, bot, user, conversation])
    db.flush()
    db.add(models.Message(conversation_id=1, role="user", content="你好"))
    db.commit()

    class LLMClient(FakeHttp):
        def __init__(self):
            super().__init__(
                FakeResp(
                    {
                        "choices": [
                            {"message": {"role": "assistant", "content": "你好呀"}}
                        ]
                    }
                )
            )

    fake = LLMClient()
    monkeypatch.setattr(bot_core.httpx, "AsyncClient", lambda *a, **k: fake)

    reply = asyncio.run(bot_core.generate_reply(db, conversation, bot))
    assert reply == "你好呀"
    url, kwargs = fake.posts[0]
    assert url == "https://api.example/v1/chat/completions"
    assert kwargs["json"]["model"] == "gpt-test"
    assert kwargs["json"]["stream"] is False
    assert any(
        m["role"] == "user" and m["content"] == "你好"
        for m in kwargs["json"]["messages"]
    )


def test_generate_reply_exposes_bound_kb_as_tool(db, monkeypatch):
    ep = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    kb = models.KnowledgeBase(
        id=1,
        name="默认库",
        provider="dify",
        base_url="https://api.dify.ai/v1",
        dataset_ids="ds-1",
        mode="llm",
        enabled=1,
    )
    bot = _bot(endpoint_id=1, model="gpt-test", kb_ids="1")
    user = models.User(id=1, nickname="u")
    conversation = models.Conversation(id=1, user_id=1, bot_id=1, title="c")
    db.add_all([ep, kb, bot, user, conversation])
    db.flush()
    db.add(models.Message(conversation_id=1, role="user", content="查下产品文档"))
    db.commit()

    tool_name = f"kb__{kb_mod._slug('默认库')}__1__retrieve"

    async def fake_retrieve(provider, base_url, api_key, dataset_ids, query, top_k=5):
        return [{"title": "T", "content": "知识内容", "source": "S"}]

    monkeypatch.setattr(bot_core, "retrieve_kb", fake_retrieve)

    class SeqLLMClient(FakeHttp):
        def __init__(self):
            super().__init__(FakeResp({}))
            self._i = 0

        async def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            if self._i == 0:
                self._i += 1
                return FakeResp(
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {
                                                "name": tool_name,
                                                "arguments": '{"query": "登录"}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                )
            return FakeResp(
                {"choices": [{"message": {"role": "assistant", "content": "文档内容"}}]}
            )

    fake = SeqLLMClient()
    monkeypatch.setattr(bot_core.httpx, "AsyncClient", lambda *a, **k: fake)

    reply = asyncio.run(bot_core.generate_reply(db, conversation, bot))
    assert reply == "文档内容"

    # 首次请求：暴露 kb 工具，且不注入系统上下文
    first_url, first_kwargs = fake.posts[0]
    tools = first_kwargs["json"].get("tools") or []
    assert any(t["function"]["name"] == tool_name for t in tools)
    assert not any(m["role"] == "system" for m in first_kwargs["json"]["messages"])

    # 第二轮请求：包含 kb 工具调用结果
    second_url, second_kwargs = fake.posts[1]
    assert any(
        m["role"] == "tool" and "知识内容" in m["content"]
        for m in second_kwargs["json"]["messages"]
    )


def test_generate_reply_exposes_web_search_tool(db, monkeypatch):
    ep = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    setting = models.Setting(id=1, search_provider="tavily", search_api_key="sk")
    bot = _bot(endpoint_id=1, model="gpt-test", web_search=1)
    user = models.User(id=1, nickname="u")
    conversation = models.Conversation(id=1, user_id=1, bot_id=1, title="c")
    db.add_all([ep, setting, bot, user, conversation])
    db.flush()
    db.add(models.Message(conversation_id=1, role="user", content="今天天气"))
    db.commit()

    searched = []

    async def fake_search(provider, api_key, base_url, query, max_results=5):
        searched.append((provider, api_key, base_url, query))
        return [{"title": "天气", "url": "http://x", "content": "晴 23度"}]

    monkeypatch.setattr(bot_core, "search_web", fake_search)

    class SeqLLMClient(FakeHttp):
        def __init__(self):
            super().__init__(FakeResp({}))
            self._i = 0

        async def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            if self._i == 0:
                self._i += 1
                return FakeResp(
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "c1",
                                            "type": "function",
                                            "function": {
                                                "name": "web_search",
                                                "arguments": '{"query": "今天天气"}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                )
            return FakeResp(
                {"choices": [{"message": {"role": "assistant", "content": "今天晴"}}]}
            )

    fake = SeqLLMClient()
    monkeypatch.setattr(bot_core.httpx, "AsyncClient", lambda *a, **k: fake)

    reply = asyncio.run(bot_core.generate_reply(db, conversation, bot))
    assert reply == "今天晴"

    first_url, first_kwargs = fake.posts[0]
    tools = first_kwargs["json"].get("tools") or []
    assert any(t["function"]["name"] == "web_search" for t in tools)

    assert searched == [("tavily", "sk", "", "今天天气")]

    second_url, second_kwargs = fake.posts[1]
    assert any(
        m["role"] == "tool" and "天气" in m["content"]
        for m in second_kwargs["json"]["messages"]
    )


def test_generate_reply_prepends_bot_system_prompt(db, monkeypatch):
    ep = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    bot = _bot(endpoint_id=1, model="gpt-test", system_prompt="你是专业助手")
    user = models.User(id=1, nickname="u")
    conversation = models.Conversation(id=1, user_id=1, bot_id=1, title="c")
    db.add_all([ep, bot, user, conversation])
    db.flush()
    db.add(models.Message(conversation_id=1, role="user", content="你好"))
    db.commit()

    class LLMClient(FakeHttp):
        def __init__(self):
            super().__init__(
                FakeResp(
                    {
                        "choices": [
                            {"message": {"role": "assistant", "content": "你好呀"}}
                        ]
                    }
                )
            )

    fake = LLMClient()
    monkeypatch.setattr(bot_core.httpx, "AsyncClient", lambda *a, **k: fake)

    reply = asyncio.run(bot_core.generate_reply(db, conversation, bot))
    assert reply == "你好呀"
    _, kwargs = fake.posts[0]
    msgs = kwargs["json"]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "你是专业助手"


def test_receive_text_flow(db, monkeypatch):
    bot = _bot()
    db.add(bot)
    db.commit()

    xml = "<xml><ToUserName>corp123</ToUserName><FromUserName>zhangsan</FromUserName><MsgType>text</MsgType><Content>在吗？</Content></xml>"
    enc_str = base64.b64encode(wc.encrypt_msg(xml, AES_KEY, "corp123")).decode()
    body = f"<xml><Encrypt>{enc_str}</Encrypt></xml>".encode()
    sig = wc.signature("token", "123", "nonce", enc_str)

    replied = {}
    sent = []

    async def fake_reply(db, conversation, bot):
        replied["conv"] = conversation.id
        return "在的，请讲"

    async def fake_send(touser, content, agent_id, corp_id, secret):
        sent.append((touser, content))

    monkeypatch.setattr(wecom_router.bot_core, "generate_reply", fake_reply)
    monkeypatch.setattr(wecom_router.bot_core, "send_text", fake_send)

    class FakeRequest:
        async def body(self):
            return body

    async def run():
        return await wecom_router.receive(
            bot_id=1,
            request=FakeRequest(),
            msg_signature=sig,
            timestamp="123",
            nonce="nonce",
            db=db,
        )

    resp = asyncio.run(run())
    assert resp.status_code == 200

    user = db.query(models.User).filter(models.User.wecom_userid == "zhangsan").first()
    assert user is not None
    conv = db.query(models.Conversation).filter(models.Conversation.bot_id == 1).first()
    assert conv is not None
    msgs = (
        db.query(models.Message).filter(models.Message.conversation_id == conv.id).all()
    )
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].content == "在吗？"
    assert msgs[1].content == "在的，请讲"
    assert sent == [("zhangsan", "在的，请讲")]


def test_receive_text_flow_json_body(db, monkeypatch):
    """企微回调以 JSON {...encrypt...} 发送时也应正常解密处理。"""
    bot = _bot()
    db.add(bot)
    db.commit()

    xml = "<xml><ToUserName>corp123</ToUserName><FromUserName>wangwu</FromUserName><MsgType>text</MsgType><Content>json消息</Content></xml>"
    enc_str = base64.b64encode(wc.encrypt_msg(xml, AES_KEY, "")).decode()
    body = json.dumps({"encrypt": enc_str}).encode()
    sig = wc.signature("token", "123", "nonce", enc_str)

    sent = []

    async def fake_reply(db, conversation, bot):
        return "收到json"

    async def fake_send(touser, content, agent_id, corp_id, secret):
        sent.append((touser, content))

    monkeypatch.setattr(wecom_router.bot_core, "generate_reply", fake_reply)
    monkeypatch.setattr(wecom_router.bot_core, "send_text", fake_send)

    class FakeRequest:
        async def body(self):
            return body

    async def run():
        return await wecom_router.receive(
            bot_id=1,
            request=FakeRequest(),
            msg_signature=sig,
            timestamp="123",
            nonce="nonce",
            db=db,
        )

    resp = asyncio.run(run())
    assert resp.status_code == 200
    user = db.query(models.User).filter(models.User.wecom_userid == "wangwu").first()
    assert user is not None
    assert sent and sent[0][1] == "收到json"


def test_receive_image_creates_attachment(db, monkeypatch):
    bot = _bot()
    db.add(bot)
    db.commit()

    xml = "<xml><ToUserName>corp123</ToUserName><FromUserName>lisi</FromUserName><MsgType>image</MsgType><MediaId>MEDIA123</MediaId></xml>"
    enc_str = base64.b64encode(wc.encrypt_msg(xml, AES_KEY, "corp123")).decode()
    body = f"<xml><Encrypt>{enc_str}</Encrypt></xml>".encode()
    sig = wc.signature("token", "123", "nonce", enc_str)

    async def fake_download(media_id, corp_id, secret):
        return b"\xff\xd8\xff" + b"abc"

    async def fake_reply(db, conversation, bot):
        return "收到图片"

    async def fake_send(*a, **k):
        pass

    monkeypatch.setattr(wecom_router.bot_core, "download_media", fake_download)
    monkeypatch.setattr(wecom_router.bot_core, "generate_reply", fake_reply)
    monkeypatch.setattr(wecom_router.bot_core, "send_text", fake_send)

    class FakeRequest:
        async def body(self):
            return body

    async def run():
        return await wecom_router.receive(
            bot_id=1,
            request=FakeRequest(),
            msg_signature=sig,
            timestamp="123",
            nonce="nonce",
            db=db,
        )

    asyncio.run(run())
    att = db.query(models.Attachment).first()
    assert att is not None
    assert att.kind == "image"
    assert att.content_type == "image/jpeg"


def test_receive_bad_signature_raises(db):
    db.add(_bot())
    db.commit()
    enc_str = "xx"
    body = f"<xml><Encrypt>{enc_str}</Encrypt></xml>".encode()

    class FakeRequest:
        async def body(self):
            return body

    with pytest.raises(Exception):
        asyncio.run(
            wecom_router.receive(
                bot_id=1,
                request=FakeRequest(),
                msg_signature="bad",
                timestamp="1",
                nonce="2",
                db=db,
            )
        )


def test_receive_missing_bot_raises(db):
    class FakeRequest:
        async def body(self):
            return b""

    with pytest.raises(Exception):
        asyncio.run(
            wecom_router.receive(
                bot_id=999,
                request=FakeRequest(),
                msg_signature="s",
                timestamp="1",
                nonce="2",
                db=db,
            )
        )


def test_verify_returns_echostr(db):
    bot = _bot()
    db.add(bot)
    db.commit()
    plain = "random-echo-string"
    enc_str = base64.b64encode(wc.encrypt_msg(plain, AES_KEY, "corp123")).decode()
    sig = wc.signature("token", "123", "nonce", enc_str)

    resp = wecom_router.verify(
        bot_id=1,
        msg_signature=sig,
        timestamp="123",
        nonce="nonce",
        echostr=enc_str,
        db=db,
    )
    assert resp.body == plain.encode()


def test_verify_accepts_empty_embedded_receive_id(db):
    """企微 URL 校验的 echostr 内嵌 receive_id 为空（实际观察），应校验成功。"""
    bot = _bot()
    db.add(bot)
    db.commit()
    plain = "random-echo-string"
    enc_str = base64.b64encode(wc.encrypt_msg(plain, AES_KEY, "")).decode()
    sig = wc.signature("token", "123", "nonce", enc_str)

    resp = wecom_router.verify(
        bot_id=1,
        msg_signature=sig,
        timestamp="123",
        nonce="nonce",
        echostr=enc_str,
        db=db,
    )
    assert resp.status_code == 200
    assert resp.body == plain.encode()


def test_parse_message_json_aibot():
    """解析企微 AI 机器人 JSON 消息。"""
    payload = json.dumps(
        {
            "msgid": "c65830ad7375758",
            "aibotid": "aibnyDOsDtf8oeifqJi6Ucj4If1Xzu6qRrz",
            "chattype": "single",
            "from": {"userid": "ZhongShengLu"},
            "msgtype": "text",
            "text": {"content": "你好"},
        }
    )
    msg = wecom_router._parse_message(payload)
    assert msg["FromUserName"] == "ZhongShengLu"
    assert msg["MsgType"] == "text"
    assert msg["Content"] == "你好"
    assert msg["ToUserName"] == "aibnyDOsDtf8oeifqJi6Ucj4If1Xzu6qRrz"


def test_parse_message_xml():
    payload = "<xml><FromUserName>w001</FromUserName><MsgType>text</MsgType><Content>hi</Content></xml>"
    msg = wecom_router._parse_message(payload)
    assert msg["FromUserName"] == "w001"
    assert msg["Content"] == "hi"
