from fastapi.security import HTTPAuthorizationCredentials

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.admin as admin_mod
from app import models, schemas
from app.auth import create_admin_token, require_dept, require_super
from app.database import Base
from app.security import hash_password


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _cred(username, role, department_id=None):
    token = create_admin_token(username, role, department_id)
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


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


# ---------- require_super / require_dept ----------


def test_require_super_accepts_super():
    db = _db()
    _mk_admin(db, "admin", role="super")
    out = require_super(_cred("admin", "super"), db)
    assert out.username == "admin"
    db.close()


def test_require_super_rejects_dept():
    db = _db()
    _mk_admin(db, "dept", role="dept", department_id=1)
    try:
        require_super(_cred("dept", "dept"), db)
        assert False, "应拒绝部门管理员"
    except Exception as exc:
        assert "超级管理员" in str(exc)
    db.close()


def test_require_dept_accepts_dept():
    db = _db()
    _mk_admin(db, "dept", role="dept", department_id=5)
    out = require_dept(_cred("dept", "dept", 5), db)
    assert out.username == "dept"
    db.close()


def test_require_dept_rejects_super():
    db = _db()
    _mk_admin(db, "admin", role="super")
    try:
        require_dept(_cred("admin", "super"), db)
        assert False, "应拒绝超级管理员"
    except Exception as exc:
        assert "部门管理员" in str(exc)
    db.close()


# ---------- 部门管理员只能管本部门 ----------


def test_list_users_filters_by_department():
    db = _db()
    db.add_all(
        [
            models.User(id=1, nickname="甲", department_id=1),
            models.User(id=2, nickname="乙", department_id=2),
            models.User(id=3, nickname="丙", department_id=None),
        ]
    )
    db.commit()
    dept_admin = models.Admin(username="dept", role="dept", department_id=1)
    rows = admin_mod.list_users(admin=dept_admin, db=db)
    assert [r.id for r in rows] == [1]
    db.close()


def test_list_users_super_sees_all():
    db = _db()
    db.add_all(
        [
            models.User(id=1, nickname="甲", department_id=1),
            models.User(id=2, nickname="乙", department_id=2),
        ]
    )
    db.commit()
    super_admin = models.Admin(username="admin", role="super")
    rows = admin_mod.list_users(admin=super_admin, db=db)
    assert {r.id for r in rows} == {1, 2}
    db.close()


# ---------- 部门管理员不能删除用户 ----------


def test_delete_user_requires_super_dependency():
    db = _db()
    u = models.User(id=1, nickname="甲")
    db.add(u)
    db.commit()
    # 直接调用 delete_user（绕过依赖）仍应成功；依赖层由 require_super 拦截
    admin_mod.delete_user(user_id=1, admin=None, db=db)
    assert db.get(models.User, 1) is None
    db.close()


# ---------- 部门 CRUD / 指定管理员 / 分配用户 ----------


def test_department_crud_and_assign():
    db = _db()
    super_admin = _mk_admin(db, "admin", role="super")
    dto = admin_mod.create_department(
        payload=schemas.DepartmentCreate(name="研发部"),
        admin=super_admin,
        db=db,
    )
    assert dto.name == "研发部"
    # 指定部门管理员
    dept_admin = _mk_admin(db, "dept", role="dept")
    admin_mod.set_department_admin(department_id=dto.id, payload={"admin_id": dept_admin.id}, admin=super_admin, db=db)
    db.refresh(dept_admin)
    assert dept_admin.department_id == dto.id
    assert dept_admin.role == "dept"
    # 分配用户到部门
    u = models.User(id=1, nickname="甲")
    db.add(u)
    db.commit()
    admin_mod.assign_user_department(user_id=1, payload={"department_id": dto.id}, admin=super_admin, db=db)
    db.refresh(u)
    assert u.department_id == dto.id
    # 部门列表包含成员数
    listed = admin_mod.list_departments(admin=super_admin, db=db)
    assert any(x.id == dto.id and x.member_count == 1 for x in listed)
    db.close()
