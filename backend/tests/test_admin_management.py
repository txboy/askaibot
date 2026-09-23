from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.routers.admin as admin_mod
from app import models, schemas
from app.database import Base
from app.security import hash_password, verify_password


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_endpoints_usage_sums_tokens_by_endpoint():
    db = _db()
    ep = models.ApiEndpoint(id=1, name="A", base_url="https://a", enabled=1)
    other = models.ApiEndpoint(id=2, name="B", base_url="https://b", enabled=1)
    msg1 = models.Message(
        conversation_id=1, role="assistant", content="x", tokens=5, endpoint_id=1,
        created_at=datetime.now(),
    )
    msg2 = models.Message(
        conversation_id=1, role="assistant", content="y", tokens=7, endpoint_id=1,
        created_at=datetime.now(),
    )
    db.add_all([ep, other, msg1, msg2])
    db.commit()
    rows = admin_mod.endpoints_usage(admin=None, db=db)
    by_id = {r["id"]: r for r in rows}
    assert by_id[1]["total_tokens"] == 12
    assert by_id[2]["total_tokens"] == 0
    assert by_id[1]["today_tokens"] == 12
    db.close()


def test_list_users_with_token_stats():
    db = _db()
    u = models.User(id=1, nickname="张三", phone="13800000000")
    conv = models.Conversation(id=1, user_id=1, title="c")
    msg = models.Message(
        conversation_id=1, role="assistant", content="x", tokens=9,
        created_at=datetime.now(),
    )
    db.add_all([u, conv, msg])
    db.commit()
    rows = admin_mod.list_users(admin=None, db=db)
    assert rows[0].nickname == "张三"
    assert rows[0].conversation_count == 1
    assert rows[0].total_tokens == 9
    assert rows[0].today_tokens == 9
    db.close()


def test_delete_user_cascades():
    db = _db()
    u = models.User(id=1, nickname="张三")
    conv = models.Conversation(id=1, user_id=1, title="c")
    msg = models.Message(conversation_id=1, role="assistant", content="x", tokens=1)
    att = models.Attachment(
        user_id=1,
        conversation_id=1,
        message_id=1,
        filename="f",
        stored_name="stored.png",
        kind="image",
    )
    db.add_all([u, conv, msg, att])
    db.commit()
    admin_mod.delete_user(user_id=1, admin=None, db=db)
    assert db.get(models.User, 1) is None
    assert db.get(models.Conversation, 1) is None
    assert db.get(models.Message, 1) is None
    assert db.get(models.Attachment, 1) is None
    db.close()


def test_change_password_verifies_old():
    db = _db()
    admin = models.Admin(id=1, username="admin", password_hash=hash_password("old"))
    db.add(admin)
    db.commit()
    admin_mod.change_password(
        payload=schemas.AdminPasswordChange(old_password="old", new_password="new"),
        admin=admin,
        db=db,
    )
    db.refresh(admin)
    assert verify_password("new", admin.password_hash)
    db.close()
