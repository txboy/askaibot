import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.admin as admin_mod
import app.controllers.frontend.endpoints as endpoints_mod
import app.controllers.frontend.mcp as mcp_mod
import app.controllers.frontend.chat as chat_mod
import app.services.groups as groups_core
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


# ---------- 组 CRUD 与授权 ----------


def test_group_crud_and_membership(db):
    u1 = models.User(id=1, nickname="张三")
    u2 = models.User(id=2, nickname="李四")
    db.add_all([u1, u2])
    db.commit()

    g = admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="研发组",
            description="研发人员",
            member_ids=[1, 2],
            grants=schemas.GroupGrantMap(mcp=[10], endpoint=[5], search=[0]),
        ),
        admin=None,
        db=db,
    )
    assert g.name == "研发组"
    assert g.member_count == 2
    assert set(g.member_ids) == {1, 2}
    assert g.grants.mcp == [10]
    assert g.grants.endpoint == [5]
    assert g.grants.search == [0]

    # 更新：只保留一个成员，改授权
    updated = admin_mod.update_group(
        group_id=g.id,
        payload=schemas.GroupUpdate(
            name="研发组A", member_ids=[1], grants=schemas.GroupGrantMap(mcp=[11])
        ),
        admin=None,
        db=db,
    )
    assert updated.name == "研发组A"
    assert updated.member_ids == [1]
    assert updated.grants.mcp == [11]
    assert updated.grants.endpoint == []


def test_group_membership_multiple_groups(db):
    u1 = models.User(id=1, nickname="张三")
    db.add(u1)
    db.commit()
    g1 = admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组1", member_ids=[1], grants=schemas.GroupGrantMap(mcp=[1])
        ),
        admin=None, db=db,
    )
    g2 = admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组2", member_ids=[1], grants=schemas.GroupGrantMap(mcp=[2])
        ),
        admin=None, db=db,
    )
    group_ids = groups_core.user_group_ids(db, 1)
    assert set(group_ids) == {g1.id, g2.id}
    # 两个组的授权并集
    assert groups_core.accessible_ids(db, 1, "mcp") == {1, 2}


def test_delete_group_cascades(db):
    g = admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组", member_ids=[1], grants=schemas.GroupGrantMap(mcp=[1])
        ),
        admin=None, db=db,
    )
    admin_mod.delete_group(group_id=g.id, admin=None, db=db)
    assert db.get(models.UserGroup, g.id) is None
    assert db.query(models.UserGroupMember).filter_by(group_id=g.id).count() == 0
    assert db.query(models.GroupGrant).filter_by(group_id=g.id).count() == 0


def test_delete_user_removes_group_memberships(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.commit()
    g = admin_mod.create_group(
        payload=schemas.GroupCreate(name="组", member_ids=[1]), admin=None, db=db
    )
    admin_mod.delete_user(user_id=1, admin=None, db=db)
    assert db.query(models.UserGroupMember).filter_by(user_id=1).count() == 0


# ---------- 资源可见性过滤 ----------


def test_public_endpoints_filters_by_scope(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.add_all(
        [
            models.ApiEndpoint(id=1, name="全局", base_url="https://a", enabled=1, scope="global"),
            models.ApiEndpoint(id=2, name="组内", base_url="https://b", enabled=1, scope="group"),
            models.ApiEndpoint(id=3, name="停用", base_url="https://c", enabled=0, scope="group"),
        ]
    )
    db.commit()
    g = admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组", member_ids=[1], grants=schemas.GroupGrantMap(endpoint=[2])
        ),
        admin=None, db=db,
    )
    rows = endpoints_mod.list_public_endpoints(user=u, db=db)
    ids = {e.id for e in rows}
    assert 1 in ids  # global 恒可见
    assert 2 in ids  # 组内被授权
    assert 3 not in ids  # 停用


def test_public_endpoints_global_ignores_groups(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.add(models.ApiEndpoint(id=1, name="全局", base_url="https://a", enabled=1, scope="global"))
    db.commit()
    rows = endpoints_mod.list_public_endpoints(user=u, db=db)
    assert len(rows) == 1  # 未加入任何组也能用 global 资源


def test_public_knowledge_bases_filters_by_scope(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.add_all(
        [
            models.KnowledgeBase(id=1, name="全局库", base_url="https://a", provider="dify", enabled=1, scope="global"),
            models.KnowledgeBase(id=2, name="组内库", base_url="https://b", provider="dify", enabled=1, scope="group"),
        ]
    )
    db.commit()
    admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组", member_ids=[1], grants=schemas.GroupGrantMap(knowledge_base=[2])
        ),
        admin=None, db=db,
    )
    rows = endpoints_mod.list_public_knowledge_bases(user=u, db=db)
    assert {k.id for k in rows} == {1, 2}


def test_public_mcp_filters_by_scope(db, monkeypatch):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.add_all(
        [
            models.McpServer(id=1, name="全局MCP", mode="frontend", enabled=1, scope="global"),
            models.McpServer(id=2, name="组内MCP", mode="frontend", enabled=1, scope="group"),
        ]
    )
    db.commit()
    admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组", member_ids=[1], grants=schemas.GroupGrantMap(mcp=[2])
        ),
        admin=None, db=db,
    )

    async def fake_list_tools(s):
        return []

    monkeypatch.setattr(mcp_mod.mcp_core, "list_tools", fake_list_tools)
    async def run():
        return await mcp_mod.list_frontend_mcp(user=u, db=db)
    rows = asyncio.run(run())
    assert {s.id for s in rows} == {1, 2}


# ---------- 搜索按组开关 ----------


def test_search_global_allows_all(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    setting = models.Setting(id=1, search_provider="tavily", search_scope="global")
    db.add(setting)
    db.commit()
    assert groups_core.can_search(db, 1, setting) is True


def test_search_group_requires_grant(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    setting = models.Setting(id=1, search_provider="tavily", search_scope="group")
    db.add(setting)
    db.commit()
    # 未授权组 → 不可用
    assert groups_core.can_search(db, 1, setting) is False
    # 授予搜索后可用
    admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组", member_ids=[1], grants=schemas.GroupGrantMap(search=[0])
        ),
        admin=None, db=db,
    )
    assert groups_core.can_search(db, 1, setting) is True


def test_search_no_provider_always_false(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    setting = models.Setting(id=1, search_provider="", search_scope="global")
    db.add(setting)
    db.commit()
    assert groups_core.can_search(db, 1, setting) is False


def test_admin_search_scope_roundtrip(db):
    admin_mod.update_search(
        payload=schemas.SearchUpdate(
            provider="tavily", api_key="k", scope="group", group_ids=[7]
        ),
        admin=None, db=db,
    )
    out = admin_mod.get_search(admin=None, db=db)
    assert out.scope == "group"
    assert out.group_ids == [7]


# ---------- 聊天越权拦截 ----------


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
        scope="global",
    )
    conversation = models.Conversation(id=1, user_id=1, title="c")
    db.add_all([user, endpoint, conversation])
    db.commit()
    return user, endpoint, conversation


def test_chat_rejects_group_endpoint_without_grant(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    endpoint.scope = "group"
    db.commit()
    fake = StreamingClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test"
    )
    import pytest as _pytest

    with _pytest.raises(Exception) as exc:
        chat_mod.chat(payload=payload, user=user, db=db)
    assert "不可用" in str(exc.value)


def test_chat_allows_group_endpoint_with_grant(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    endpoint.scope = "group"
    db.commit()
    admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组", member_ids=[1], grants=schemas.GroupGrantMap(endpoint=[1])
        ),
        admin=None, db=db,
    )
    fake = StreamingClient()
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
    assert "你好" in output


def test_chat_ignores_group_kb_without_grant(db, monkeypatch):
    user, endpoint, conversation = _chat_setup(db)
    db.add(
        models.KnowledgeBase(
            id=1, name="KB", provider="dify", base_url="https://x",
            dataset_ids="ds-1", enabled=1, scope="group",
        )
    )
    db.commit()

    async def fake_retrieve(provider, base_url, api_key, dataset_ids, query, top_k=5):
        return [{"title": "T", "content": "知识", "source": "S"}]

    monkeypatch.setattr(chat_mod, "retrieve_kb", fake_retrieve)
    fake = StreamingClient()
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test",
        knowledge_base_id=1,
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    output = asyncio.run(collect())
    assert "你好" in output
    msgs = fake.jsons[0]["messages"]
    assert not any(m["role"] == "system" and "知识" in m["content"] for m in msgs)


# ---------- 技能 group scope ----------


def test_user_skills_includes_group_scope(db):
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.add_all(
        [
            models.Skill(id=1, name="全局技能", scope="global", enabled=1, tools="[]"),
            models.Skill(id=2, name="组内技能", scope="group", enabled=1, tools="[]"),
            models.Skill(id=3, name="其他组技能", scope="group", enabled=1, tools="[]"),
        ]
    )
    db.commit()
    admin_mod.create_group(
        payload=schemas.GroupCreate(
            name="组", member_ids=[1], grants=schemas.GroupGrantMap(skill=[2])
        ),
        admin=None, db=db,
    )
    from app.services import skills as skill_core

    names = {s.name for s in skill_core.user_skills(db, 1)}
    assert names == {"全局技能", "组内技能"}
