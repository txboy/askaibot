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
from app.auth import create_admin_token, get_current_admin
from app.common import get_setting, mask_key
from app.config import config
from app.database import get_db
from app.security import hash_password, verify_password
from app.services import groups as groups_core

router = APIRouter()
__all__ = ["create_knowledge_base", "delete_knowledge_base", "list_knowledge_bases", "test_knowledge_base", "update_knowledge_base"]

def _kb_out(kb: models.KnowledgeBase, db: Session) -> schemas.KnowledgeBaseOut:
    return schemas.KnowledgeBaseOut(
        id=kb.id,
        name=kb.name,
        provider=kb.provider,
        base_url=kb.base_url,
        api_key_masked=mask_key(kb.api_key),
        dataset_ids=kb.dataset_ids,
        top_k=kb.top_k,
        mode=kb.mode,
        description=kb.description,
        enabled=kb.enabled,
        scope=kb.scope or "global",
        group_ids=groups_core.group_ids_for_resource(db, "knowledge_base", kb.id),
    )

@router.get("/knowledge-bases", response_model=list[schemas.KnowledgeBaseOut])
def list_knowledge_bases(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_kb_out(kb, db) for kb in db.query(models.KnowledgeBase).all()]

@router.post("/knowledge-bases", response_model=schemas.KnowledgeBaseOut)
def create_knowledge_base(
    payload: schemas.KnowledgeBaseCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = models.KnowledgeBase(
        name=payload.name,
        provider=payload.provider or "dify",
        base_url=payload.base_url,
        api_key=payload.api_key or "",
        dataset_ids=payload.dataset_ids or "",
        top_k=payload.top_k or 5,
        mode=payload.mode or "frontend",
        description=payload.description or "",
        enabled=payload.enabled or 1,
        scope=payload.scope or "global",
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _kb_out(kb, db)

@router.put("/knowledge-bases/{kb_id}", response_model=schemas.KnowledgeBaseOut)
def update_knowledge_base(
    kb_id: int,
    payload: schemas.KnowledgeBaseUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if payload.name is not None:
        kb.name = payload.name
    if payload.provider is not None:
        kb.provider = payload.provider
    if payload.base_url is not None:
        kb.base_url = payload.base_url
    if payload.api_key:
        kb.api_key = payload.api_key
    if payload.dataset_ids is not None:
        kb.dataset_ids = payload.dataset_ids
    if payload.top_k is not None:
        kb.top_k = payload.top_k
    if payload.mode is not None:
        kb.mode = payload.mode
    if payload.description is not None:
        kb.description = payload.description
    if payload.enabled is not None:
        kb.enabled = payload.enabled
    if payload.scope is not None:
        kb.scope = payload.scope
    db.commit()
    db.refresh(kb)
    if payload.group_ids is not None:
        groups_core.set_resource_grants(db, "knowledge_base", kb.id, payload.group_ids)
        db.commit()
        db.refresh(kb)
    return _kb_out(kb, db)

@router.delete("/knowledge-bases/{kb_id}")
def delete_knowledge_base(
    kb_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    groups_core.set_resource_grants(db, "knowledge_base", kb.id, [])
    db.delete(kb)
    db.commit()
    return {"ok": True}

@router.post("/knowledge-bases/test", response_model=dict)
async def test_knowledge_base(
    payload: schemas.KnowledgeBaseTestRequest,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    results = await retrieve_kb(
        payload.provider,
        payload.base_url,
        payload.api_key,
        payload.dataset_ids,
        payload.query,
        top_k=payload.top_k,
    )
    return {"ok": True, "count": len(results), "results": results}