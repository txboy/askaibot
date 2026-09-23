import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.routers.admin as admin_mod
import app.routers.chat as chat_mod
import app.mcp as mcp_core
from app import models, schemas
from app.database import Base


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


class _TextBlock:
    def __init__(self, text):
        self.text = text


class _FakeResult:
    def __init__(self, content):
        self.content = content


# ---------- 纯函数 ----------


def test_function_name_namespacing():
    assert mcp_core.function_name("My Server", "get time") == "mcp__My_Server__get_time"
    assert mcp_core.function_name("", "x")[0:5] == "mcp__"
    assert "mcp__" in mcp_core.function_name("S", "t")


def test_parse_json_and_ids():
    assert mcp_core._parse_json('{"a":1}', {}) == {"a": 1}
    assert mcp_core._parse_json("", []) == []
    assert mcp_core._parse_json("bad", {}) == {}
    assert mcp_core.parse_ids("1,2,3") == [1, 2, 3]
    assert mcp_core.parse_ids("") == []
    assert mcp_core.parse_ids("a,b,4") == [4]


def test_extract_text_joins_blocks():
    result = _FakeResult([_TextBlock("hello"), _TextBlock("world")])
    assert mcp_core._extract_text(result) == "hello\nworld"


# ---------- 工具 schema 转换 ----------


def test_build_openai_tools(monkeypatch):
    server = models.McpServer(id=1, name="news", enabled=1)

    async def fake_list(s):
        return [
            {
                "name": "fetch",
                "description": "fetch news",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

    monkeypatch.setattr(mcp_core, "list_tools", fake_list)

    async def run():
        tools, mapping = await mcp_core.build_openai_tools([server])
        return tools, mapping

    tools, mapping = asyncio.run(run())
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "mcp__news__fetch"
    assert "mcp__news__fetch" in mapping
    assert mapping["mcp__news__fetch"][0] is server
    assert mapping["mcp__news__fetch"][1] == "fetch"


# ---------- 管理后台 CRUD ----------


def test_admin_create_mcp_masks_headers():
    db = _db()
    out = admin_mod.create_mcp_server(
        payload=schemas.McpServerCreate(
            name="天气",
            mode="frontend",
            transport="http",
            url="https://mcp.example/mcp",
            headers='{"Authorization":"Bearer sk-12345678"}',
        ),
        admin=None,
        db=db,
    )
    assert out.name == "天气"
    assert out.mode == "frontend"
    assert "sk-12345678" not in out.headers_masked
    assert "****" in out.headers_masked
    assert db.get(models.McpServer, 1).mode == "frontend"
    db.close()


def test_admin_update_and_delete_mcp():
    db = _db()
    s = models.McpServer(id=1, name="A", mode="llm", enabled=1, headers="{}")
    db.add(s)
    db.commit()
    out = admin_mod.update_mcp_server(
        server_id=1,
        payload=schemas.McpServerUpdate(mode="frontend", enabled=0),
        admin=None,
        db=db,
    )
    assert out.mode == "frontend"
    assert out.enabled == 0
    assert admin_mod.delete_mcp_server(server_id=1, admin=None, db=db) == {"ok": True}
    assert db.get(models.McpServer, 1) is None
    db.close()


def test_admin_create_mcp_tolerates_non_dict_headers():
    db = _db()
    out = admin_mod.create_mcp_server(
        payload=schemas.McpServerCreate(name="x", headers="123"),
        admin=None,
        db=db,
    )
    assert out.headers_masked == "{}"
    db.close()


def test_admin_test_mcp_server(monkeypatch):
    db = _db()
    s = models.McpServer(id=1, name="A", headers="{}", enabled=1)
    db.add(s)
    db.commit()

    async def fake_list(server):
        return [{"name": "get", "description": "d", "input_schema": {}}]

    monkeypatch.setattr(admin_mod.mcp_core, "list_tools", fake_list)
    out = asyncio.run(admin_mod.test_mcp_server(server_id=1, admin=None, db=db))
    assert out[0].name == "get"
    db.close()


# ---------- 聊天集成 ----------


class _FakeStreamResp:
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


class _FakeHttpClient:
    def __init__(self, first_tool_name):
        self.jsons = []
        self._first = first_tool_name

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def stream(self, method, url, headers=None, json=None):
        self.jsons.append(json)
        if len(self.jsons) == 1:
            lines = [
                'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"'
                + self._first
                + '","arguments":"{}"}}]}}]}',
                "data: [DONE]",
            ]
        else:
            lines = [
                'data: {"choices":[{"delta":{"content":"结果"}}]}',
                'data: {"choices":[{"delta":{}}],"usage":{"total_tokens":7}}',
                "data: [DONE]",
            ]
        return _FakeStreamResp(lines)


def test_chat_injects_mcp_tool_and_routes(monkeypatch):
    db = _db()
    user = models.User(id=1, nickname="张三")
    endpoint = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    conversation = models.Conversation(id=1, user_id=1, title="c", mcp_ids="2")
    setting = models.Setting(id=1)
    server = models.McpServer(
        id=2, name="weather", mode="frontend", enabled=1, headers="{}"
    )
    db.add_all([user, endpoint, conversation, setting, server])
    db.commit()

    calls = []
    fake_server = server

    async def fake_build(servers):
        return (
            [
                {
                    "type": "function",
                    "function": {
                        "name": "mcp__weather__get_weather",
                        "description": "get weather",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            {"mcp__weather__get_weather": (fake_server, "get_weather")},
        )

    async def fake_call(srv, tool_name, arguments):
        calls.append((srv, tool_name, arguments))
        return "今天晴，25度"

    monkeypatch.setattr(chat_mod.mcp_core, "build_openai_tools", fake_build)
    monkeypatch.setattr(chat_mod.mcp_core, "call_tool", fake_call)
    fake = _FakeHttpClient("mcp__weather__get_weather")
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test"
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    output = asyncio.run(collect())

    assert "mcp__weather__get_weather" in str(fake.jsons[0].get("tools"))
    assert "tools" not in (fake.jsons[1] or {})
    assert calls and calls[0][1] == "get_weather" and calls[0][2] == {}
    assert '"status"' in output
    assert "结果" in output
    db.close()


def test_chat_mcp_only_injects_when_selected(monkeypatch):
    db = _db()
    user = models.User(id=1, nickname="张三")
    endpoint = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    conversation = models.Conversation(id=1, user_id=1, title="c", mcp_ids="")
    setting = models.Setting(id=1)
    server = models.McpServer(
        id=2, name="weather", mode="frontend", enabled=1, headers="{}"
    )
    db.add_all([user, endpoint, conversation, setting, server])
    db.commit()

    async def fake_build(servers):
        return [], {}

    monkeypatch.setattr(chat_mod.mcp_core, "build_openai_tools", fake_build)
    fake = _FakeHttpClient("mcp__weather__get_weather")
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test"
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    output = asyncio.run(collect())
    assert not fake.jsons[0].get("tools")
    db.close()
