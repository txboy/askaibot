from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.routers.admin as admin_mod
from app import models, schemas
from app.database import Base


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_create_wecom_bot_masks_secret_and_callback():
    db = _db()
    db.add(models.Setting(id=1, wecom_redirect="https://oabot.example"))
    db.commit()
    out = admin_mod.create_wecom_bot(
        payload=schemas.WecomBotCreate(
            name="客服",
            corp_id="corp",
            secret="secret-key",
            agent_id="1000002",
            token="tok12345",
            aes_key="abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG",
            enabled=1,
        ),
        admin=None,
        db=db,
    )
    assert out.name == "客服"
    assert out.token_masked != "tok12345"
    assert out.aes_key_set is True
    assert out.callback_url == "https://oabot.example/api/wecom/bot/1/callback"
    db.close()


def test_update_wecom_bot():
    db = _db()
    bot = models.WecomBot(id=1, name="A", token="abc", enabled=1)
    db.add(bot)
    db.commit()
    out = admin_mod.update_wecom_bot(
        bot_id=1,
        payload=schemas.WecomBotUpdate(
            name="B", web_search=1, kb_ids="3,5", endpoint_id=None
        ),
        admin=None,
        db=db,
    )
    assert out.name == "B"
    assert out.web_search == 1
    assert out.kb_ids == "3,5"
    db.close()


def test_delete_wecom_bot():
    db = _db()
    bot = models.WecomBot(id=1, name="A", token="abc", enabled=1)
    db.add(bot)
    db.commit()
    r = admin_mod.delete_wecom_bot(bot_id=1, admin=None, db=db)
    assert r == {"ok": True}
    assert db.get(models.WecomBot, 1) is None
    db.close()
