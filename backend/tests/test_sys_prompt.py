import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.common import resolve_system_prompt, user_platform
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


def test_user_platform_detection(db):
    assert user_platform(models.User(id=1, feishu_userid="ou_1")) == "feishu"
    assert user_platform(models.User(id=1, dingtalk_userid="dt_1")) == "dingtalk"
    assert user_platform(models.User(id=1, wecom_userid="wm_1")) == "wecom"
    assert user_platform(models.User(id=1)) == ""
    assert user_platform(None) == ""
    m = models.User(id=1, wecom_userid="wm_1", feishu_userid="ou_1")
    assert user_platform(m) == "feishu"


def _setting(**kw):
    return models.Setting(id=1, **kw)


def test_resolve_priority_bot_highest(db):
    db.add(_setting(system_prompt="global"))
    bot = models.WecomBot(id=1, name="bot", provider="feishu", system_prompt="bot")
    endpoint = models.ApiEndpoint(
        id=1, name="ep", base_url="https://x/v1", system_prompt="endpoint"
    )
    db.add_all([bot, endpoint])
    db.commit()
    assert resolve_system_prompt(db, bot=bot, endpoint=endpoint) == "bot"


def test_resolve_falls_to_platform_when_no_bot_prompt(db):
    db.add(_setting(feishu_system_prompt="platform"))
    bot = models.WecomBot(id=1, name="bot", provider="feishu", system_prompt="")
    endpoint = models.ApiEndpoint(
        id=1, name="ep", base_url="https://x/v1", system_prompt="endpoint"
    )
    db.add_all([bot, endpoint])
    db.commit()
    assert resolve_system_prompt(db, bot=bot, endpoint=endpoint) == "platform"


def test_resolve_provider_param_for_chat(db):
    db.add(_setting(dingtalk_system_prompt="dd_platform", system_prompt="global"))
    endpoint = models.ApiEndpoint(
        id=1, name="ep", base_url="https://x/v1", system_prompt="endpoint"
    )
    db.add(endpoint)
    db.commit()
    # 聊天场景：无 bot，传入用户注册平台 provider
    assert (
        resolve_system_prompt(db, endpoint=endpoint, provider="dingtalk")
        == "dd_platform"
    )
    # 普通用户（无 provider）：跳过基础配置，落到接口
    assert resolve_system_prompt(db, endpoint=endpoint, provider="") == "endpoint"


def test_resolve_falls_to_endpoint_then_global(db):
    db.add(_setting(system_prompt="global"))
    endpoint = models.ApiEndpoint(
        id=1, name="ep", base_url="https://x/v1", system_prompt="endpoint"
    )
    db.add(endpoint)
    db.commit()
    assert resolve_system_prompt(db, endpoint=endpoint) == "endpoint"
    assert resolve_system_prompt(db, endpoint=None) == "global"


def test_resolve_returns_empty_when_nothing_set(db):
    db.add(_setting())
    db.commit()
    assert resolve_system_prompt(db) == ""
