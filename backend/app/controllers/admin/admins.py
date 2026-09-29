from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import require_super
from app.database import get_db
from app.security import hash_password
from app.services.audit import audit

router = APIRouter()
__all__ = ["create_admin", "delete_admin", "list_admins", "update_admin"]


def _admin_out(db: Session, a: models.Admin) -> schemas.AdminOut:
    department_name = None
    if a.department_id:
        d = db.get(models.Department, a.department_id)
        department_name = d.name if d else None
    return schemas.AdminOut(
        id=a.id,
        username=a.username,
        role=a.role,
        department_id=a.department_id,
        department_name=department_name,
    )


@router.get("/admins", response_model=list[schemas.AdminOut])
def list_admins(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    return [_admin_out(db, a) for a in db.query(models.Admin).all()]


@router.post("/admins", response_model=schemas.AdminOut)
def create_admin(
    payload: schemas.AdminCreate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    if db.query(models.Admin).filter(models.Admin.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if payload.role not in ("super", "dept"):
        raise HTTPException(status_code=400, detail="角色不合法")
    a = models.Admin(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        department_id=payload.department_id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    audit(
        db,
        admin,
        action="admin.create",
        target_type="admin",
        target_id=a.id,
        summary=f"创建管理员 {a.username} ({a.role})",
    )
    db.commit()
    return _admin_out(db, a)


@router.put("/admins/{admin_id}", response_model=schemas.AdminOut)
def update_admin(
    admin_id: int,
    payload: schemas.AdminUpdate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    a = db.get(models.Admin, admin_id)
    if not a:
        raise HTTPException(status_code=404, detail="管理员不存在")
    if payload.role is not None and payload.role not in ("super", "dept"):
        raise HTTPException(status_code=400, detail="角色不合法")
    if payload.password:
        a.password_hash = hash_password(payload.password)
    if payload.role is not None:
        a.role = payload.role
    if payload.department_id is not None:
        a.department_id = payload.department_id or None
    db.commit()
    audit(
        db,
        admin,
        action="admin.update",
        target_type="admin",
        target_id=a.id,
        summary=f"更新管理员 {a.username}",
    )
    db.commit()
    return _admin_out(db, a)


@router.delete("/admins/{admin_id}")
def delete_admin(
    admin_id: int,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    a = db.get(models.Admin, admin_id)
    if not a:
        raise HTTPException(status_code=404, detail="管理员不存在")
    if a.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    audit(
        db,
        admin,
        action="admin.delete",
        target_type="admin",
        target_id=a.id,
        summary=f"删除管理员 {a.username}",
    )
    db.delete(a)
    db.commit()
    return {"ok": True}
