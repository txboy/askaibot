import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.admin as admin_mod
import app.controllers.frontend.auth as auth_mod
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


def test_agreement_crud(db):
    a1 = admin_mod.create_agreement(
        payload=schemas.AgreementCreate(
            title="用户协议", content="第一条：...", enabled=1, required=1
        ),
        admin=None, db=db,
    )
    a2 = admin_mod.create_agreement(
        payload=schemas.AgreementCreate(
            title="隐私政策", content="...", enabled=0, required=0
        ),
        admin=None, db=db,
    )
    assert a1.title == "用户协议"
    assert a1.required == 1

    rows = admin_mod.list_agreements(admin=None, db=db)
    assert {r.id for r in rows} == {a1.id, a2.id}

    updated = admin_mod.update_agreement(
        agreement_id=a1.id,
        payload=schemas.AgreementUpdate(title="用户协议V2", required=0),
        admin=None, db=db,
    )
    assert updated.title == "用户协议V2"
    assert updated.required == 0

    admin_mod.delete_agreement(agreement_id=a1.id, admin=None, db=db)
    assert db.get(models.Agreement, a1.id) is None


def test_public_agreements_only_enabled(db):
    admin_mod.create_agreement(
        payload=schemas.AgreementCreate(title="A", content="c", enabled=1),
        admin=None, db=db,
    )
    admin_mod.create_agreement(
        payload=schemas.AgreementCreate(title="B", content="c", enabled=0),
        admin=None, db=db,
    )
    rows = auth_mod.list_public_agreements(db=db)
    assert [r.title for r in rows] == ["A"]


def test_agreement_status_and_agree(db):
    admin_mod.create_agreement(
        payload=schemas.AgreementCreate(title="必填", content="c", enabled=1, required=1),
        admin=None, db=db,
    )
    admin_mod.create_agreement(
        payload=schemas.AgreementCreate(title="非必填", content="c", enabled=1, required=0),
        admin=None, db=db,
    )
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.commit()

    pending = auth_mod.agreement_status(user=u, db=db)
    assert [p.title for p in pending] == ["必填"]

    auth_mod.agree(payload=schemas.AgreeRequest(agreement_ids=[p.id for p in pending]), user=u, db=db)
    assert auth_mod.agreement_status(user=u, db=db) == []
    assert u.agreed_at is not None


def test_agree_is_idempotent(db):
    a = admin_mod.create_agreement(
        payload=schemas.AgreementCreate(title="必填", content="c", enabled=1, required=1),
        admin=None, db=db,
    )
    u = models.User(id=1, nickname="张三")
    db.add(u)
    db.commit()
    for _ in range(2):
        auth_mod.agree(payload=schemas.AgreeRequest(agreement_ids=[a.id]), user=u, db=db)
    assert u.agreed_agreement_ids == str(a.id)
