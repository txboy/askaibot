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
__all__ = [
    "create_endpoint",
    "delete_endpoint",
    "endpoints_usage",
    "list_endpoints",
    "update_endpoint",
]


def _endpoint_out(e: models.ApiEndpoint, db: Session) -> schemas.EndpointOut:
    return schemas.EndpointOut(
        id=e.id,
        name=e.name,
        base_url=e.base_url,
        api_key_masked=mask_key(e.api_key),
        models=e.models,
        enabled=e.enabled,
        is_default=e.is_default,
        scope=e.scope or "global",
        system_prompt=e.system_prompt or "",
        group_ids=groups_core.group_ids_for_resource(db, "endpoint", e.id),
    )


@router.get("/endpoints", response_model=list[schemas.EndpointOut])
def list_endpoints(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_endpoint_out(e, db) for e in db.query(models.ApiEndpoint).all()]


@router.post("/endpoints", response_model=schemas.EndpointOut)
def create_endpoint(
    payload: schemas.EndpointCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = models.ApiEndpoint(
        name=payload.name,
        base_url=payload.base_url,
        api_key=payload.api_key or "",
        models=payload.models or "",
        enabled=payload.enabled or 1,
        is_default=payload.is_default or 0,
        scope=payload.scope or "global",
        system_prompt=payload.system_prompt or "",
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint, db)


@router.get("/endpoints/usage")
def endpoints_usage(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    today_start = datetime.combine(datetime.now().date(), time.min)
    month_start = datetime(datetime.now().year, datetime.now().month, 1)
    result = []
    for e in db.query(models.ApiEndpoint).all():
        total = (
            db.query(func.coalesce(func.sum(models.Message.tokens), 0))
            .filter(models.Message.endpoint_id == e.id)
            .scalar()
        )
        today = (
            db.query(func.coalesce(func.sum(models.Message.tokens), 0))
            .filter(
                models.Message.endpoint_id == e.id,
                models.Message.created_at >= today_start,
            )
            .scalar()
        )
        month = (
            db.query(func.coalesce(func.sum(models.Message.tokens), 0))
            .filter(
                models.Message.endpoint_id == e.id,
                models.Message.created_at >= month_start,
            )
            .scalar()
        )
        result.append(
            {
                "id": e.id,
                "name": e.name,
                "base_url": e.base_url,
                "is_default": e.is_default,
                "enabled": e.enabled,
                "today_tokens": today,
                "month_tokens": month,
                "total_tokens": total,
            }
        )
    return result


@router.put("/endpoints/{endpoint_id}", response_model=schemas.EndpointOut)
def update_endpoint(
    endpoint_id: int,
    payload: schemas.EndpointUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = db.get(models.ApiEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    if payload.name is not None:
        endpoint.name = payload.name
    if payload.base_url is not None:
        endpoint.base_url = payload.base_url
    if payload.api_key:
        endpoint.api_key = payload.api_key
    if payload.models is not None:
        endpoint.models = payload.models
    if payload.enabled is not None:
        endpoint.enabled = payload.enabled
    if payload.is_default is not None:
        endpoint.is_default = payload.is_default
        if payload.is_default:
            db.query(models.ApiEndpoint).filter(
                models.ApiEndpoint.id != endpoint.id
            ).update({"is_default": 0})
    if payload.scope is not None:
        endpoint.scope = payload.scope
    if payload.system_prompt is not None:
        endpoint.system_prompt = payload.system_prompt
    db.commit()
    db.refresh(endpoint)
    if payload.group_ids is not None:
        groups_core.set_resource_grants(db, "endpoint", endpoint.id, payload.group_ids)
        db.commit()
        db.refresh(endpoint)
    return _endpoint_out(endpoint, db)


@router.delete("/endpoints/{endpoint_id}")
def delete_endpoint(
    endpoint_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = db.get(models.ApiEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    groups_core.set_resource_grants(db, "endpoint", endpoint.id, [])
    db.delete(endpoint)
    db.commit()
    return {"ok": True}
