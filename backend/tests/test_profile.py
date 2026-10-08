from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
import app.controllers.frontend.auth as auth_mod
from app.database import Base
from app.controllers.frontend.auth import update_phone, update_profile


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_update_profile_updates_nickname(db):
    from app import schemas

    user = models.User(id=1, nickname="张三")
    db.add(user)
    db.commit()
    result = update_profile(
        payload=schemas.ProfileUpdate(nickname="李四"), user=user, db=db
    )
    assert result.nickname == "李四"


def test_update_profile_updates_assistant_name(db):
    from app import schemas

    user = models.User(id=1, nickname="张三")
    db.add(user)
    db.commit()
    result = update_profile(
        payload=schemas.ProfileUpdate(assistant_name="小助手"), user=user, db=db
    )
    assert result.assistant_name == "小助手"
    assert result.nickname == "张三"


def test_update_profile_requires_nickname(db):
    user = models.User(id=1, nickname="张三")
    from app import schemas

    with pytest.raises(HTTPException) as exc:
        update_profile(payload=schemas.ProfileUpdate(nickname="   "), user=user, db=db)
    assert exc.value.status_code == 400


def test_update_phone_valid_code_binds(db):
    from app import schemas

    user = models.User(id=1, nickname="张三", phone="13800000001")
    db.add(user)
    db.commit()
    auth_mod._sms_codes["13900000002"] = {
        "code": "123456",
        "expires": datetime.now() + timedelta(minutes=5),
    }
    result = update_phone(
        payload=schemas.PhoneUpdate(phone="13900000002", code="123456"),
        user=user,
        db=db,
    )
    assert result.phone == "13900000002"


def test_update_phone_wrong_code(db):
    from app import schemas

    user = models.User(id=1, nickname="张三", phone="13800000001")
    db.add(user)
    db.commit()
    auth_mod._sms_codes["13900000002"] = {
        "code": "123456",
        "expires": datetime.now() + timedelta(minutes=5),
    }
    with pytest.raises(HTTPException) as exc:
        update_phone(
            payload=schemas.PhoneUpdate(phone="13900000002", code="000000"),
            user=user,
            db=db,
        )
    assert exc.value.status_code == 400


def test_update_phone_rejects_taken_phone(db):
    from app import schemas

    other = models.User(id=2, nickname="李四", phone="13900000009")
    user = models.User(id=1, nickname="张三", phone="13800000001")
    db.add_all([other, user])
    db.commit()
    auth_mod._sms_codes["13900000009"] = {
        "code": "123456",
        "expires": datetime.now() + timedelta(minutes=5),
    }
    with pytest.raises(HTTPException) as exc:
        update_phone(
            payload=schemas.PhoneUpdate(phone="13900000009", code="123456"),
            user=user,
            db=db,
        )
    assert exc.value.status_code == 400
