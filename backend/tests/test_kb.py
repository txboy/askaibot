import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.kb as kb_mod
import app.routers.admin as admin_mod
import app.routers.chat as chat_mod
import app.routers.endpoints as endpoints_mod
from app import models, schemas
from app.database import Base


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


class FakeResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.posts = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse(
            {
                "results": [
                    {"title": "标题", "content": "内容", "source": "来源"},
                ]
            }
        )


def test_retrieve_kb_posts_contract(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    results = asyncio.run(
        kb_mod.retrieve_kb(
            "https://kb.example/retrieve", "k-123", "如何登录？", top_k=5
        )
    )

    assert len(fake.posts) == 1
    url, kwargs = fake.posts[0]
    assert url == "https://kb.example/retrieve"
    assert kwargs["json"] == {"query": "如何登录？", "top_k": 5}
    assert kwargs["headers"]["Authorization"] == "Bearer k-123"
    assert results and results[0]["title"] == "标题"


def test_retrieve_kb_no_api_key_omits_header(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    asyncio.run(kb_mod.retrieve_kb("https://kb.example/retrieve", "", "hi"))

    url, kwargs = fake.posts[0]
    assert "Authorization" not in kwargs.get("headers", {})


def test_retrieve_kb_degrades_on_error(monkeypatch):
    class ErrClient(FakeClient):
        async def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            raise RuntimeError("network down")

    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: ErrClient())

    assert (
        asyncio.run(kb_mod.retrieve_kb("https://kb.example/retrieve", "", "hi")) == []
    )


def test_retrieve_kb_empty_results(monkeypatch):
    class EmptyClient(FakeClient):
        async def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            return FakeResponse({"results": []})

    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: EmptyClient())

    assert (
        asyncio.run(kb_mod.retrieve_kb("https://kb.example/retrieve", "", "hi")) == []
    )


def test_admin_create_kb(db):
    out = admin_mod.create_knowledge_base(
        payload=schemas.KnowledgeBaseCreate(
            name="内部文档",
            base_url="https://kb.example/retrieve",
            api_key="secret-key",
            description="内部资料",
            enabled=1,
        ),
        admin=None,
        db=db,
    )
    assert out.name == "内部文档"
    assert out.api_key_masked == "secr****-key"


def test_admin_list_kb(db):
    admin_mod.create_knowledge_base(
        payload=schemas.KnowledgeBaseCreate(
            name="A", base_url="https://x/retrieve", api_key="k123", enabled=1
        ),
        admin=None,
        db=db,
    )
    items = admin_mod.list_knowledge_bases(admin=None, db=db)
    assert len(items) == 1
    assert items[0].name == "A"
    assert items[0].api_key_masked != "k123"


def test_admin_update_kb(db):
    kb = models.KnowledgeBase(
        name="A", base_url="https://x/retrieve", api_key="old", enabled=1
    )
    db.add(kb)
    db.commit()
    out = admin_mod.update_knowledge_base(
        kb_id=kb.id,
        payload=schemas.KnowledgeBaseUpdate(
            name="B", base_url="https://y/retrieve", api_key="newkey"
        ),
        admin=None,
        db=db,
    )
    assert out.name == "B"
    db.refresh(kb)
    assert kb.base_url == "https://y/retrieve"
    assert kb.api_key == "newkey"


def test_admin_delete_kb(db):
    kb = models.KnowledgeBase(name="A", base_url="https://x/retrieve", enabled=1)
    db.add(kb)
    db.commit()
    r = admin_mod.delete_knowledge_base(kb_id=kb.id, admin=None, db=db)
    assert r == {"ok": True}
    assert db.get(models.KnowledgeBase, kb.id) is None


def test_public_list_kb_only_enabled(db):
    db.add_all(
        [
            models.KnowledgeBase(
                name="已启用", base_url="https://x/retrieve", enabled=1
            ),
            models.KnowledgeBase(
                name="已停用", base_url="https://y/retrieve", enabled=0
            ),
        ]
    )
    db.commit()
    items = endpoints_mod.list_public_knowledge_bases(user=None, db=db)
    assert len(items) == 1
    assert items[0].name == "已启用"


class ChunkStreamResp:
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


class StreamingClient:
    def __init__(self):
        self.jsons = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def stream(self, method, url, headers=None, json=None):
        self.jsons.append(json)
        return ChunkStreamResp(
            [
                'data: {"choices":[{"delta":{"content":"你好"}}]}',
                'data: {"choices":[{"delta":{}}],"usage":{"total_tokens":3}}',
                "data: [DONE]",
            ]
        )


def _chat_setup(db):
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
    db.add_all([user, endpoint, conversation])
    db.commit()
    return user, endpoint, conversation


def _collect(resp):
    async def _run():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    return asyncio.run(_run())


def test_chat_injects_kb_context(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    db.add(
        models.KnowledgeBase(
            id=1,
            name="KB",
            base_url="https://kb.example/retrieve",
            api_key="sk",
            enabled=1,
        )
    )
    db.commit()

    async def fake_retrieve(base_url, api_key, query, top_k=5):
        return [{"title": "T", "content": "知识内容", "source": "S"}]

    monkeypatch.setattr(chat_mod, "retrieve_kb", fake_retrieve)
    fake = StreamingClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1,
        content="怎么登录？",
        endpoint_id=1,
        model="gpt-test",
        knowledge_base_id=1,
    )
    output = _collect(chat_mod.chat(payload=payload, user=user, db=db))

    assert "你好" in output
    msgs = fake.jsons[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert "知识内容" in msgs[0]["content"]


def test_chat_no_kb_context_when_empty(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    db.add(
        models.KnowledgeBase(
            id=1,
            name="KB",
            base_url="https://kb.example/retrieve",
            api_key="sk",
            enabled=1,
        )
    )
    db.commit()

    async def fake_retrieve(base_url, api_key, query, top_k=5):
        return []

    monkeypatch.setattr(chat_mod, "retrieve_kb", fake_retrieve)
    fake = StreamingClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1,
        content="hi",
        endpoint_id=1,
        model="gpt-test",
        knowledge_base_id=1,
    )
    _collect(chat_mod.chat(payload=payload, user=user, db=db))

    msgs = fake.jsons[0]["messages"]
    assert not any(m["role"] == "system" for m in msgs)


def test_chat_invalid_kb_skips_context(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    fake = StreamingClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1,
        content="hi",
        endpoint_id=1,
        model="gpt-test",
        knowledge_base_id=999,
    )
    _collect(chat_mod.chat(payload=payload, user=user, db=db))

    msgs = fake.jsons[0]["messages"]
    assert not any(m["role"] == "system" for m in msgs)
