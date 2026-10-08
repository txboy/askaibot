from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.admin as admin_mod
from app import models, schemas
from app.database import Base
from app.security import hash_password


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _mk_admin(db, username, role="super", department_id=None):
    a = models.Admin(
        username=username,
        password_hash=hash_password("123456"),
        role=role,
        department_id=department_id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_delete_user_writes_audit_log(db=None):
    db = _db()
    super_admin = _mk_admin(db, "admin", role="super")
    u = models.User(id=1, nickname="甲")
    db.add(u)
    db.commit()
    admin_mod.delete_user(user_id=1, admin=super_admin, db=db)
    log = db.query(models.AuditLog).filter_by(action="user.delete").first()
    assert log is not None
    assert log.admin_username == "admin"
    assert log.target_type == "user"
    assert log.target_id == 1
    db.close()


def test_create_endpoint_writes_audit_log():
    db = _db()
    super_admin = _mk_admin(db, "admin", role="super")
    admin_mod.create_endpoint(
        payload=schemas.EndpointCreate(name="接口", base_url="https://a", api_key="k"),
        admin=super_admin,
        db=db,
    )
    log = db.query(models.AuditLog).filter_by(action="endpoint.create").first()
    assert log is not None
    assert log.admin_role == "super"
    db.close()


def test_audit_log_list_and_export():
    db = _db()
    super_admin = _mk_admin(db, "admin", role="super")
    db.add(
        models.AuditLog(
            admin_id=super_admin.id,
            admin_username="admin",
            admin_role="super",
            action="system.update",
            target_type="system",
            target_id=0,
            summary="更新系统设置",
            created_at=datetime.now(),
        )
    )
    db.commit()
    page = admin_mod.list_audit_logs(page=1, size=20, _admin=super_admin, db=db)
    assert page.total == 1
    assert page.items[0].action == "system.update"
    resp = admin_mod.export_audit_logs(_admin=super_admin, db=db)
    assert "action" in (resp.body.decode("utf-8-sig"))
    db.close()


def test_audit_log_filter_by_action():
    db = _db()
    super_admin = _mk_admin(db, "admin", role="super")
    db.add_all(
        [
            models.AuditLog(admin_username="admin", action="user.delete", target_type="user", target_id=1, created_at=datetime.now()),
            models.AuditLog(admin_username="admin", action="admin.create", target_type="admin", target_id=2, created_at=datetime.now()),
        ]
    )
    db.commit()
    page = admin_mod.list_audit_logs(page=1, size=20, action="user.delete", _admin=super_admin, db=db)
    assert page.total == 1
    assert page.items[0].action == "user.delete"
    db.close()
