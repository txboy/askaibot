import json
import os
import shutil
import uuid
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.services import mcp as mcp_core
from app.services import skills as skill_core
from app.services.kb import retrieve_kb
from app.auth import create_admin_token, require_super
from app.common import get_setting, mask_key
from app.config import config
from app.database import get_db
from app.security import hash_password, verify_password
from app.services import groups as groups_core
from app.services.audit import audit

router = APIRouter()
__all__ = ["create_group", "delete_group", "list_groups", "update_group"]

_TRANS = {
    "endpoint": "endpoint",
    "knowledge_base": "knowledge_base",
    "mcp": "mcp",
    "search": "search",
    "skill": "skill",
}


def _grants_map(db: Session, group_id: int) -> schemas.GroupGrantMap:
    rows = (
        db.query(models.GroupGrant)
        .filter(models.GroupGrant.group_id == group_id)
        .all()
    )
    data = {
        "endpoint": [],
        "knowledge_base": [],
        "mcp": [],
        "search": [],
        "skill": [],
    }
    for r in rows:
        if r.resource_type in data:
            data[r.resource_type].append(r.resource_id)
    return schemas.GroupGrantMap(**data)


def _apply_grants(db: Session, group_id: int, grants: schemas.GroupGrantMap) -> None:
    db.query(models.GroupGrant).filter(
        models.GroupGrant.group_id == group_id
    ).delete(synchronize_session=False)
    for rtype in _TRANS:
        for rid in getattr(grants, rtype) or []:
            db.add(
                models.GroupGrant(
                    group_id=group_id,
                    resource_type=rtype,
                    resource_id=int(rid),
                )
            )


def _group_out(db: Session, g: models.UserGroup) -> schemas.GroupOut:
    member_ids = [
        m.user_id
        for m in db.query(models.UserGroupMember)
        .filter(models.UserGroupMember.group_id == g.id)
        .all()
    ]
    return schemas.GroupOut(
        id=g.id,
        name=g.name,
        description=g.description,
        member_ids=member_ids,
        member_count=len(member_ids),
        grants=_grants_map(db, g.id),
    )


@router.get("/groups", response_model=list[schemas.GroupOut])
def list_groups(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    return [_group_out(db, g) for g in db.query(models.UserGroup).all()]


@router.post("/groups", response_model=schemas.GroupOut)
def create_group(
    payload: schemas.GroupCreate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    group = models.UserGroup(
        name=payload.name,
        description=payload.description or "",
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    for uid in payload.member_ids or []:
        db.add(models.UserGroupMember(group_id=group.id, user_id=int(uid)))
    _apply_grants(db, group.id, payload.grants)
    db.commit()
    db.refresh(group)
    audit(
        db,
        admin,
        action="group.create",
        target_type="group",
        target_id=group.id,
        summary=f"创建用户组 {group.name}",
    )
    db.commit()
    return _group_out(db, group)


@router.put("/groups/{group_id}", response_model=schemas.GroupOut)
def update_group(
    group_id: int,
    payload: schemas.GroupUpdate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    group = db.get(models.UserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="用户组不存在")
    if payload.name is not None:
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    db.commit()
    if payload.member_ids is not None:
        db.query(models.UserGroupMember).filter(
            models.UserGroupMember.group_id == group.id
        ).delete(synchronize_session=False)
        for uid in payload.member_ids:
            db.add(models.UserGroupMember(group_id=group.id, user_id=int(uid)))
    if payload.grants is not None:
        _apply_grants(db, group.id, payload.grants)
    db.commit()
    db.refresh(group)
    audit(
        db,
        admin,
        action="group.update",
        target_type="group",
        target_id=group.id,
        summary=f"更新用户组 {group.name}",
    )
    db.commit()
    return _group_out(db, group)


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    group = db.get(models.UserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="用户组不存在")
    audit(
        db,
        admin,
        action="group.delete",
        target_type="group",
        target_id=group.id,
        summary=f"删除用户组 {group.name}",
    )
    db.query(models.UserGroupMember).filter(
        models.UserGroupMember.group_id == group.id
    ).delete(synchronize_session=False)
    db.query(models.GroupGrant).filter(
        models.GroupGrant.group_id == group.id
    ).delete(synchronize_session=False)
    db.delete(group)
    db.commit()
    return {"ok": True}
