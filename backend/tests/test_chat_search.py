import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.frontend.chat as chat_mod
from app import models, schemas
from app.database import Base


class FakeStreamResp:
    def __init__(self, lines, status=200):
        self._lines = lines
        self.status_code = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def aread(self):
        return b"mock error"

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class FakeHttpClient:
    def __init__(self, *args, **kwargs):
        self.jsons = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, headers=None, json=None):
        self.jsons.append(json)
        if len(self.jsons) == 1:
            lines = [
                'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"web_search","arguments":"{\\"query\\":\\"hello\\"}"}}]}}]}',
                "data: [DONE]",
            ]
        else:
            lines = [
                'data: {"choices":[{"delta":{"content":"答案是"}}]}',
                'data: {"choices":[{"delta":{"content":"42。"}}]}',
                'data: {"choices":[{"delta":{}}],"usage":{"total_tokens":10}}',
                "data: [DONE]",
            ]
        return FakeStreamResp(lines)


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


def test_chat_web_search_tool_flow(db, monkeypatch):
    user = models.User(id=1, nickname="张三")
    endpoint = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    conversation = models.Conversation(id=1, user_id=1, title="c")
    setting = models.Setting(id=1, search_provider="tavily", search_api_key="sk")
    db.add_all([user, endpoint, conversation, setting])
    db.commit()

    async def fake_search(provider, api_key, base_url, query):
        return [{"title": "T", "url": "U", "content": "C"}]

    monkeypatch.setattr(chat_mod, "search_web", fake_search)
    fake = FakeHttpClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1,
        content="hi",
        endpoint_id=1,
        model="gpt-test",
        web_search=True,
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    output = asyncio.run(collect())

    assert fake.jsons[0].get("tools"), "第一轮应注入 tools"
    assert "tools" not in (fake.jsons[1] or {}), "第二轮不应带 tools"
    assert "正在联网搜索" in output or '"status"' in output
    assert '"delta"' in output
    assert "答案是" in output and "42。" in output

    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == 1, models.Message.role == "assistant")
        .all()
    )
    assert messages and messages[0].content == "答案是42。"
    assert messages[0].tokens == 10


def test_chat_injects_platform_system_prompt(db, monkeypatch):
    user = models.User(id=1, nickname="张三", feishu_userid="ou_1")
    endpoint = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    conversation = models.Conversation(id=1, user_id=1, title="c")
    setting = models.Setting(id=1, feishu_system_prompt="飞书助手提示词")
    db.add_all([user, endpoint, conversation, setting])
    db.commit()

    fake = FakeHttpClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1,
        content="hi",
        endpoint_id=1,
        model="gpt-test",
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    asyncio.run(collect())
    msgs = fake.jsons[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "飞书助手提示词"


def test_chat_injects_endpoint_system_prompt(db, monkeypatch):
    user = models.User(id=1, nickname="张三")
    endpoint = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
        system_prompt="接口提示词",
    )
    conversation = models.Conversation(id=1, user_id=1, title="c")
    db.add_all([user, endpoint, conversation])
    db.commit()

    fake = FakeHttpClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1,
        content="hi",
        endpoint_id=1,
        model="gpt-test",
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    asyncio.run(collect())
    msgs = fake.jsons[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "接口提示词"


def test_chat_web_search_disabled_no_tools(db, monkeypatch):
    user = models.User(id=1, nickname="张三")
    endpoint = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    conversation = models.Conversation(id=1, user_id=1, title="c")
    setting = models.Setting(id=1, search_provider="")
    db.add_all([user, endpoint, conversation, setting])
    db.commit()

    fake = FakeHttpClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1,
        content="hi",
        endpoint_id=1,
        model="gpt-test",
        web_search=False,
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    output = asyncio.run(collect())
    assert not fake.jsons[0].get("tools")
    assert '"delta"' in output
