from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import require_super, require_dept
from app.database import get_db
from app.services.audit import audit

router = APIRouter()
__all__ = [
    "create_department",
    "delete_department",
    "dept_stats",
    "list_departments",
    "set_department_admin",
    "update_department",
    "mine_department",
]


def _dept_out(db: Session, d: models.Department) -> schemas.DepartmentOut:
    member_count = (
        db.query(models.User)
        .filter(models.User.department_id == d.id)
        .count()
    )
    admin = (
        db.query(models.Admin)
        .filter(models.Admin.department_id == d.id, models.Admin.role == "dept")
        .first()
    )
    return schemas.DepartmentOut(
        id=d.id,
        name=d.name,
        description=d.description or "",
        member_count=member_count,
        admin_id=admin.id if admin else None,
        admin_username=admin.username if admin else None,
        created_at=d.created_at,
    )


@router.get("/departments", response_model=list[schemas.DepartmentOut])
def list_departments(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    return [_dept_out(db, d) for d in db.query(models.Department).all()]


@router.post("/departments", response_model=schemas.DepartmentOut)
def create_department(
    payload: schemas.DepartmentCreate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    d = models.Department(name=payload.name, description=payload.description or "")
    db.add(d)
    db.commit()
    db.refresh(d)
    audit(
        db,
        admin,
        action="department.create",
        target_type="department",
        target_id=d.id,
        summary=f"创建部门 {d.name}",
    )
    db.commit()
    return _dept_out(db, d)


@router.put("/departments/{department_id}", response_model=schemas.DepartmentOut)
def update_department(
    department_id: int,
    payload: schemas.DepartmentUpdate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    d = db.get(models.Department, department_id)
    if not d:
        raise HTTPException(status_code=404, detail="部门不存在")
    if payload.name is not None:
        d.name = payload.name
    if payload.description is not None:
        d.description = payload.description
    db.commit()
    audit(
        db,
        admin,
        action="department.update",
        target_type="department",
        target_id=d.id,
        summary=f"更新部门 {d.name}",
    )
    db.commit()
    return _dept_out(db, d)


@router.delete("/departments/{department_id}")
def delete_department(
    department_id: int,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    d = db.get(models.Department, department_id)
    if not d:
        raise HTTPException(status_code=404, detail="部门不存在")
    db.query(models.User).filter(
        models.User.department_id == d.id
    ).update({models.User.department_id: None})
    db.query(models.Admin).filter(
        models.Admin.department_id == d.id
    ).update({models.Admin.department_id: None})
    audit(
        db,
        admin,
        action="department.delete",
        target_type="department",
        target_id=d.id,
        summary=f"删除部门 {d.name}",
    )
    db.delete(d)
    db.commit()
    return {"ok": True}


@router.put("/departments/{department_id}/admins", response_model=schemas.DepartmentOut)
def set_department_admin(
    department_id: int,
    payload: dict,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    d = db.get(models.Department, department_id)
    if not d:
        raise HTTPException(status_code=404, detail="部门不存在")
    admin_id = payload.get("admin_id")
    # 清除该部门原有部门管理员
    db.query(models.Admin).filter(
        models.Admin.department_id == d.id, models.Admin.role == "dept"
    ).update({models.Admin.department_id: None})
    if admin_id:
        target = db.get(models.Admin, int(admin_id))
        if not target:
            raise HTTPException(status_code=404, detail="管理员不存在")
        db.query(models.Admin).filter(
            models.Admin.id == target.id
        ).update(
            {
                models.Admin.department_id: d.id,
                models.Admin.role: "dept",
            }
        )
    db.commit()
    audit(
        db,
        admin,
        action="department.set_admin",
        target_type="department",
        target_id=d.id,
        summary=f"设置部门 {d.name} 管理员",
    )
    db.commit()
    return _dept_out(db, d)


# ---------- 部门管理员自己的部门数据 ----------


@router.get("/departments/mine", response_model=schemas.DepartmentOut)
def mine_department(
    admin: models.Admin = Depends(require_dept),
    db: Session = Depends(get_db),
):
    d = db.get(models.Department, admin.department_id)
    if not d:
        raise HTTPException(status_code=404, detail="部门不存在")
    return _dept_out(db, d)


@router.get("/departments/mine/stats")
def dept_stats(
    admin: models.Admin = Depends(require_dept),
    db: Session = Depends(get_db),
):
    user_ids = [
        u.id
        for u in db.query(models.User)
        .filter(models.User.department_id == admin.department_id)
        .all()
    ]
    if not user_ids:
        return {"users": 0, "conversations": 0, "messages": 0, "total_tokens": 0, "today_tokens": 0}

    from datetime import datetime, time

    today_start = datetime.combine(datetime.now().date(), time.min)
    conv_ids = [
        c.id
        for c in db.query(models.Conversation)
        .filter(models.Conversation.user_id.in_(user_ids))
        .all()
    ]
    conv_count = len(conv_ids)
    msg_q = db.query(models.Message)
    if conv_ids:
        msg_q = msg_q.filter(models.Message.conversation_id.in_(conv_ids))
    else:
        msg_q = msg_q.filter(models.Message.id < 0)
    msg_count = msg_q.count()
    token_sum = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .filter(models.Message.conversation_id.in_(conv_ids))
        .scalar()
        if conv_ids
        else 0
    )
    today_tokens = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .filter(
            models.Message.conversation_id.in_(conv_ids),
            models.Message.created_at >= today_start,
        )
        .scalar()
        if conv_ids
        else 0
    )
    return {
        "users": len(user_ids),
        "conversations": conv_count,
        "messages": msg_count,
        "total_tokens": token_sum,
        "today_tokens": today_tokens,
    }
