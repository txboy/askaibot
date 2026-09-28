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
    def __init__(self, data=None, *args, **kwargs):
        self.posts = []
        self._data = data or {"records": []}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse(self._data)


def _collect(resp):
    async def _run():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    return asyncio.run(_run())


# --- Dify ---


def test_retrieve_dify_posts_contract(monkeypatch):
    fake = FakeClient(
        data={
            "records": [{"segment": {"content": "内容", "document": {"name": "来源"}}}]
        }
    )
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    results = asyncio.run(
        kb_mod.retrieve_kb(
            "dify", "https://kb.example/v1", "k-123", "ds-1,ds-2", "如何登录？", top_k=5
        )
    )

    assert len(fake.posts) == 1
    url, kwargs = fake.posts[0]
    assert url == "https://kb.example/v1/datasets/ds-1/retrieve"
    assert kwargs["json"]["query"] == "如何登录？"
    assert kwargs["json"]["retrieval_model"]["search_method"] == "hybrid_search"
    assert kwargs["json"]["retrieval_model"]["top_k"] == 5
    assert kwargs["headers"]["Authorization"] == "Bearer k-123"
    assert results and results[0]["content"] == "内容"
    assert results[0]["source"] == "来源"


def test_retrieve_dify_empty_records(monkeypatch):
    fake = FakeClient(data={"records": []})
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    assert (
        asyncio.run(
            kb_mod.retrieve_kb("dify", "https://kb.example/v1", "", "ds-1", "hi")
        )
        == []
    )


# --- RAGFlow ---


def test_retrieve_ragflow_posts_contract(monkeypatch):
    fake = FakeClient(
        data={
            "code": 0,
            "data": {"chunks": [{"content": "c1", "document_name": "doc1"}]},
        }
    )
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    results = asyncio.run(
        kb_mod.retrieve_kb(
            "ragflow", "http://host:9380", "rk", "ds-1,ds-2", "hi", top_k=3
        )
    )

    assert len(fake.posts) == 1
    url, kwargs = fake.posts[0]
    assert url == "http://host:9380/api/v1/retrieval"
    assert kwargs["json"] == {
        "question": "hi",
        "dataset_ids": ["ds-1", "ds-2"],
        "page_size": 3,
    }
    assert kwargs["headers"]["Authorization"] == "Bearer rk"
    assert results and results[0]["content"] == "c1"
    assert results[0]["source"] == "doc1"


def test_retrieve_ragflow_nonzero_code_returns_empty(monkeypatch):
    fake = FakeClient(data={"code": 102, "message": "dataset_ids is required."})
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    assert (
        asyncio.run(kb_mod.retrieve_kb("ragflow", "http://host:9380", "", "ds-1", "hi"))
        == []
    )


# --- shared behaviour ---


def test_retrieve_kb_no_api_key_omits_header(monkeypatch):
    fake = FakeClient(data={"records": []})
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    asyncio.run(kb_mod.retrieve_kb("dify", "https://kb.example/v1", "", "ds-1", "hi"))
    _, kwargs = fake.posts[0]
    assert "Authorization" not in kwargs.get("headers", {})


def test_retrieve_kb_missing_dataset_returns_empty(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    assert (
        asyncio.run(kb_mod.retrieve_kb("dify", "https://kb.example/v1", "", "", "hi"))
        == []
    )
    assert (
        asyncio.run(
            kb_mod.retrieve_kb("dify", "https://kb.example/v1", "", "  ,", "hi")
        )
        == []
    )


def test_retrieve_kb_missing_base_url_returns_empty(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    assert asyncio.run(kb_mod.retrieve_kb("dify", "", "", "ds-1", "hi")) == []


def test_retrieve_kb_unknown_provider_returns_empty(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    assert (
        asyncio.run(
            kb_mod.retrieve_kb("generic", "https://kb.example/v1", "", "ds-1", "hi")
        )
        == []
    )


def test_retrieve_kb_degrades_on_error(monkeypatch):
    class ErrClient(FakeClient):
        async def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            raise RuntimeError("network down")

    monkeypatch.setattr(kb_mod.httpx, "AsyncClient", lambda *a, **k: ErrClient())
    assert (
        asyncio.run(
            kb_mod.retrieve_kb("dify", "https://kb.example/v1", "", "ds-1", "hi")
        )
        == []
    )


# --- admin CRUD ---


def test_admin_create_kb(db):
    out = admin_mod.create_knowledge_base(
        payload=schemas.KnowledgeBaseCreate(
            name="内部文档",
            provider="dify",
            base_url="https://api.dify.ai/v1",
            api_key="secret-key",
            dataset_ids="ds-1",
            top_k=8,
            description="内部资料",
            enabled=1,
        ),
        admin=None,
        db=db,
    )
    assert out.name == "内部文档"
    assert out.provider == "dify"
    assert out.dataset_ids == "ds-1"
    assert out.top_k == 8
    assert out.api_key_masked == "secr****-key"


def test_admin_create_ragflow_defaults(db):
    out = admin_mod.create_knowledge_base(
        payload=schemas.KnowledgeBaseCreate(
            name="A", provider="ragflow", base_url="http://host:9380", enabled=1
        ),
        admin=None,
        db=db,
    )
    assert out.provider == "ragflow"
    assert out.top_k == 5


def test_admin_list_kb(db):
    admin_mod.create_knowledge_base(
        payload=schemas.KnowledgeBaseCreate(
            name="A", base_url="https://x", api_key="k123", enabled=1
        ),
        admin=None,
        db=db,
    )
    items = admin_mod.list_knowledge_bases(admin=None, db=db)
    assert len(items) == 1
    assert items[0].name == "A"
    assert items[0].api_key_masked != "k123"


def test_admin_update_kb(db):
    kb = models.KnowledgeBase(name="A", base_url="https://x", api_key="old", enabled=1)
    db.add(kb)
    db.commit()
    out = admin_mod.update_knowledge_base(
        kb_id=kb.id,
        payload=schemas.KnowledgeBaseUpdate(
            name="B", base_url="https://y", dataset_ids="ds-9", top_k=10
        ),
        admin=None,
        db=db,
    )
    assert out.name == "B"
    assert out.dataset_ids == "ds-9"
    assert out.top_k == 10
    db.refresh(kb)
    assert kb.base_url == "https://y"


def test_admin_delete_kb(db):
    kb = models.KnowledgeBase(name="A", base_url="https://x", enabled=1)
    db.add(kb)
    db.commit()
    r = admin_mod.delete_knowledge_base(kb_id=kb.id, admin=None, db=db)
    assert r == {"ok": True}
    assert db.get(models.KnowledgeBase, kb.id) is None


def test_admin_test_kb(monkeypatch, db):
    captured = {}

    async def fake_retrieve(provider, base_url, api_key, dataset_ids, query, top_k=5):
        captured.update(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            dataset_ids=dataset_ids,
            query=query,
            top_k=top_k,
        )
        return [{"title": "T", "content": "C", "source": "S"}]

    monkeypatch.setattr(admin_mod, "retrieve_kb", fake_retrieve)
    res = asyncio.run(
        admin_mod.test_knowledge_base(
            payload=schemas.KnowledgeBaseTestRequest(
                provider="ragflow",
                base_url="http://host:9380",
                api_key="rk",
                dataset_ids="ds-1",
                top_k=7,
                query="hi",
            ),
            admin=None,
            db=db,
        )
    )
    assert res["count"] == 1
    assert captured["provider"] == "ragflow"
    assert captured["top_k"] == 7


def test_public_list_kb_only_enabled(db):
    db.add_all(
        [
            models.KnowledgeBase(
                name="已启用", base_url="https://x/retrieve", provider="dify", enabled=1
            ),
            models.KnowledgeBase(
                name="已停用",
                base_url="https://y/retrieve",
                provider="ragflow",
                enabled=0,
            ),
        ]
    )
    db.commit()
    items = endpoints_mod.list_public_knowledge_bases(user=None, db=db)
    assert len(items) == 1
    assert items[0].name == "已启用"
    assert items[0].provider == "dify"


def test_public_list_excludes_llm_mode(db):
    db.add_all(
        [
            models.KnowledgeBase(
                name="前台库",
                base_url="https://x",
                provider="dify",
                mode="frontend",
                enabled=1,
            ),
            models.KnowledgeBase(
                name="默认库",
                base_url="https://y",
                provider="ragflow",
                mode="llm",
                enabled=1,
            ),
        ]
    )
    db.commit()
    items = endpoints_mod.list_public_knowledge_bases(user=None, db=db)
    assert [i.name for i in items] == ["前台库"]


def test_build_openai_tools(db):
    kb1 = models.KnowledgeBase(
        id=1,
        name="产品文档",
        provider="dify",
        base_url="https://x",
        dataset_ids="ds-1",
        mode="llm",
        enabled=1,
    )
    kb2 = models.KnowledgeBase(
        id=2,
        name="产品文档",
        provider="ragflow",
        base_url="https://y",
        dataset_ids="ds-2",
        mode="llm",
        enabled=1,
    )
    db.add_all([kb1, kb2])
    db.commit()

    tools, mapping = kb_mod.build_openai_tools([kb1, kb2])
    assert len(tools) == 2
    names = {t["function"]["name"] for t in tools}
    assert all(n.startswith("kb__") for n in names)
    assert "产品文档" in tools[0]["function"]["description"]
    # 两个同名知识库通过 id 去重，名称不冲突
    assert len(names) == 2
    assert mapping[list(names)[0]] in (kb1, kb2)


def test_admin_create_llm_mode_kb(db):
    out = admin_mod.create_knowledge_base(
        payload=schemas.KnowledgeBaseCreate(
            name="默认库", provider="dify", base_url="https://x", mode="llm", enabled=1
        ),
        admin=None,
        db=db,
    )
    assert out.mode == "llm"


# --- chat 使用模式 ---


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


def test_chat_injects_kb_context(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    db.add(
        models.KnowledgeBase(
            id=1,
            name="KB",
            provider="dify",
            base_url="https://api.dify.ai/v1",
            api_key="sk",
            dataset_ids="ds-1",
            top_k=5,
            enabled=1,
        )
    )
    db.commit()

    async def fake_retrieve(provider, base_url, api_key, dataset_ids, query, top_k=5):
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
            base_url="https://api.dify.ai/v1",
            api_key="sk",
            dataset_ids="ds-1",
            enabled=1,
        )
    )
    db.commit()

    async def fake_retrieve(provider, base_url, api_key, dataset_ids, query, top_k=5):
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


def test_chat_exposes_llm_kb_as_tool(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    db.add(
        models.KnowledgeBase(
            id=1,
            name="默认库",
            provider="dify",
            base_url="https://api.dify.ai/v1",
            dataset_ids="ds-1",
            mode="llm",
            enabled=1,
        )
    )
    db.commit()
    fake = StreamingClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test"
    )
    _collect(chat_mod.chat(payload=payload, user=user, db=db))

    tools = fake.jsons[0].get("tools") or []
    assert any(t["function"]["name"].startswith("kb__") for t in tools)

    # llm 模式库不作为系统提示注入
    msgs = fake.jsons[0]["messages"]
    assert not any(m["role"] == "system" for m in msgs)


def test_chat_selecting_llm_kb_does_not_inject(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    db.add(
        models.KnowledgeBase(
            id=1,
            name="默认库",
            provider="dify",
            base_url="https://api.dify.ai/v1",
            dataset_ids="ds-1",
            mode="llm",
            enabled=1,
        )
    )
    db.commit()
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


def test_chat_handles_kb_tool_call(db, monkeypatch):
    """模型调用 kb 工具时，把知识库内容作为 tool 结果返回。"""
    user, endpoint, conversation = _chat_setup(db)
    db.add(
        models.KnowledgeBase(
            id=1,
            name="默认库",
            provider="dify",
            base_url="https://api.dify.ai/v1",
            dataset_ids="ds-1",
            mode="llm",
            enabled=1,
        )
    )
    db.commit()

    async def fake_retrieve(provider, base_url, api_key, dataset_ids, query, top_k=5):
        return [{"title": "T", "content": "知识内容", "source": "S"}]

    monkeypatch.setattr(chat_mod, "retrieve_kb", fake_retrieve)

    tool_name = f"kb__{kb_mod._slug('默认库')}__1__retrieve"

    class ToolStreamClient(StreamingClient):
        def __init__(self):
            super().__init__()
            self._round = 0

        def stream(self, method, url, headers=None, json=None):
            self.jsons.append(json)
            if self._round == 0:
                self._round += 1
                return ChunkStreamResp(
                    [
                        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"%s","arguments":"{\\"query\\":\\"登录\\"}"}}]}}]}'
                        % tool_name,
                        "data: [DONE]",
                    ]
                )
            return ChunkStreamResp(
                [
                    'data: {"choices":[{"delta":{"content":"答案"}}]}',
                    'data: {"choices":[{"delta":{}}],"usage":{"total_tokens":3}}',
                    "data: [DONE]",
                ]
            )

    fake = ToolStreamClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test"
    )
    output = _collect(chat_mod.chat(payload=payload, user=user, db=db))

    assert "答案" in output
    # 第二轮请求应包含 kb 工具结果
    second = fake.jsons[1]
    assert any(
        m["role"] == "tool" and "知识内容" in m["content"] for m in second["messages"]
    )
