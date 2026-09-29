import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.frontend.chat as chat_mod
from app import models, schemas
from app.database import Base
from app.services import quota as quota_core


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


def _setting(db, **kw):
    s = models.Setting(id=1, **kw)
    db.add(s)
    return s


# ---------- effective_token_limit 优先级 ----------


def test_priority_personal_over_department_over_system(db):
    dept = models.Department(id=1, name="研发部", token_limit_daily=500)
    db.add(dept)
    _setting(db, token_limit_daily=1000)
    # 个人设置最高优先
    user = models.User(id=1, nickname="甲", department_id=1, token_limit_daily=200)
    db.commit()
    assert quota_core.effective_token_limit(db, user) == 200
    # 个人未设置 -> 部门
    user2 = models.User(id=2, nickname="乙", department_id=1)
    db.commit()
    assert quota_core.effective_token_limit(db, user2) == 500
    # 个人、部门均未设置 -> 系统
    user3 = models.User(id=3, nickname="丙")
    db.commit()
    assert quota_core.effective_token_limit(db, user3) == 1000


def test_all_empty_returns_none(db):
    _setting(db)
    user = models.User(id=1, nickname="甲")
    db.commit()
    assert quota_core.effective_token_limit(db, user) is None


def test_zero_treated_as_unset(db):
    _setting(db, token_limit_daily=0)
    dept = models.Department(id=1, name="研发部", token_limit_daily=0)
    db.add(dept)
    user = models.User(id=1, nickname="甲", department_id=1, token_limit_daily=0)
    db.commit()
    assert quota_core.effective_token_limit(db, user) is None


# ---------- used_tokens_today ----------


def test_used_tokens_today_counts_today_only(db):
    user = models.User(id=1, nickname="甲")
    conv1 = models.Conversation(id=1, user_id=1, title="c1")
    conv2 = models.Conversation(id=2, user_id=1, title="c2")
    other = models.Conversation(id=3, user_id=99, title="c3")
    db.add_all([user, conv1, conv2, other])
    db.commit()
    now = datetime.now()
    today_late = now - timedelta(hours=1)
    yesterday = now - timedelta(days=1)
    db.add_all(
        [
            models.Message(conversation_id=1, role="assistant", content="a", tokens=10, created_at=today_late),
            models.Message(conversation_id=2, role="assistant", content="b", tokens=5, created_at=now),
            models.Message(conversation_id=1, role="assistant", content="c", tokens=8, created_at=yesterday),
            models.Message(conversation_id=3, role="assistant", content="d", tokens=100, created_at=now),
        ]
    )
    db.commit()
    assert quota_core.used_tokens_today(db, 1) == 15


def test_used_tokens_today_no_messages(db):
    user = models.User(id=1, nickname="甲")
    db.add(user)
    db.commit()
    assert quota_core.used_tokens_today(db, 1) == 0


# ---------- token_limit_status ----------


def test_token_limit_status(db):
    _setting(db, token_limit_daily=100)
    user = models.User(id=1, nickname="甲")
    conv = models.Conversation(id=1, user_id=1, title="c")
    db.add_all([user, conv])
    db.commit()
    today_late = datetime.now() - timedelta(hours=1)
    db.add(
        models.Message(conversation_id=1, role="assistant", content="a", tokens=30, created_at=today_late)
    )
    db.commit()
    status = quota_core.token_limit_status(db, user)
    assert status == {"limit": 100, "used": 30, "remaining": 70}


def test_token_limit_status_unlimited(db):
    _setting(db)
    user = models.User(id=1, nickname="甲")
    db.add(user)
    db.commit()
    status = quota_core.token_limit_status(db, user)
    assert status["limit"] is None
    assert status["remaining"] is None


def test_token_limit_status_exhausted(db):
    _setting(db, token_limit_daily=50)
    user = models.User(id=1, nickname="甲")
    conv = models.Conversation(id=1, user_id=1, title="c")
    db.add_all([user, conv])
    db.commit()
    today_late = datetime.now() - timedelta(hours=1)
    db.add(
        models.Message(conversation_id=1, role="assistant", content="a", tokens=60, created_at=today_late)
    )
    db.commit()
    status = quota_core.token_limit_status(db, user)
    assert status == {"limit": 50, "used": 60, "remaining": 0}


# ---------- chat 拦截 ----------


class FakeHttpClient:
    def __init__(self, *args, **kwargs):
        self.jsons = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, headers=None, json=None):
        self.jsons.append(json)
        return FakeStreamResp(
            [
                'data: {"choices":[{"delta":{"content":"hi"}}]}',
                'data: {"choices":[{"delta":{}}],"usage":{"total_tokens":10}}',
                "data: [DONE]",
            ]
        )


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


def test_chat_blocked_when_over_limit(db):
    _setting(db, token_limit_daily=10)
    user, endpoint, conversation = _chat_setup(db)
    # 今日已用 15 >= 10
    today_late = datetime.now() - timedelta(hours=1)
    db.add(
        models.Message(conversation_id=1, role="assistant", content="a", tokens=15, created_at=today_late)
    )
    db.commit()
    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test"
    )
    try:
        chat_mod.chat(payload=payload, user=user, db=db)
        assert False, "应触发 429"
    except HTTPException as exc:
        assert exc.status_code == 429
        assert "限额" in exc.detail


def test_chat_allowed_when_under_limit(db, monkeypatch):
    _setting(db, token_limit_daily=100)
    user, endpoint, conversation = _chat_setup(db)
    fake = FakeHttpClient()
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
    assert '"delta"' in output
    # 回复已落库
    assistant_msgs = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == 1, models.Message.role == "assistant")
        .all()
    )
    assert assistant_msgs and assistant_msgs[0].content == "hi"
