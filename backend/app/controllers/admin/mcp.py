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
    "create_mcp_server",
    "delete_mcp_server",
    "list_mcp_servers",
    "refresh_mcp_server",
    "test_mcp_server",
    "update_mcp_server",
]

_SECRET_HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "token",
    "key",
    "secret",
    "x-auth-token",
}


def _mask_headers(headers) -> dict:
    out: dict = {}
    if not isinstance(headers, dict):
        return out
    for k, v in headers.items():
        if k.lower() in _SECRET_HEADER_KEYS:
            out[k] = mask_key(str(v))
        else:
            out[k] = v
    return out


def _mcp_out(server: models.McpServer, db: Session) -> schemas.McpServerOut:
    tools = [
        schemas.McpToolOut(
            name=t["name"],
            description=t.get("description") or "",
            input_schema=t.get("input_schema") or {},
        )
        for t in (mcp_core.get_cached_tools(server.id) or [])
    ]
    headers = {}
    try:
        parsed = json.loads(server.headers or "{}")
        if isinstance(parsed, dict):
            headers = parsed
    except Exception:
        headers = {}
    return schemas.McpServerOut(
        id=server.id,
        name=server.name,
        description=server.description,
        transport=server.transport,
        url=server.url,
        headers_masked=str(_mask_headers(headers)),
        command=server.command,
        args=server.args,
        env_set=bool(server.env and server.env != "{}"),
        mode=server.mode,
        enabled=server.enabled,
        scope=server.scope or "global",
        group_ids=groups_core.group_ids_for_resource(db, "mcp", server.id),
        tools=tools,
    )


@router.get("/mcp", response_model=list[schemas.McpServerOut])
def list_mcp_servers(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_mcp_out(s, db) for s in db.query(models.McpServer).all()]


@router.post("/mcp", response_model=schemas.McpServerOut)
def create_mcp_server(
    payload: schemas.McpServerCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = models.McpServer(
        name=payload.name,
        description=payload.description or "",
        transport=payload.transport or "http",
        url=payload.url or "",
        headers=payload.headers or "{}",
        command=payload.command or "",
        args=payload.args or "[]",
        env=payload.env or "{}",
        mode=payload.mode or "llm",
        enabled=payload.enabled or 1,
        scope=payload.scope or "global",
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return _mcp_out(server, db)


@router.put("/mcp/{server_id}", response_model=schemas.McpServerOut)
def update_mcp_server(
    server_id: int,
    payload: schemas.McpServerUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    for field in (
        "name",
        "description",
        "transport",
        "url",
        "headers",
        "command",
        "args",
        "env",
        "mode",
        "scope",
    ):
        val = getattr(payload, field)
        if val is not None:
            setattr(server, field, val)
    if payload.enabled is not None:
        server.enabled = payload.enabled
    db.commit()
    db.refresh(server)
    if payload.group_ids is not None:
        groups_core.set_resource_grants(db, "mcp", server.id, payload.group_ids)
        db.commit()
        db.refresh(server)
    mcp_core.clear_cache(server.id)
    return _mcp_out(server, db)


@router.delete("/mcp/{server_id}")
def delete_mcp_server(
    server_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    groups_core.set_resource_grants(db, "mcp", server.id, [])
    db.delete(server)
    db.commit()
    mcp_core.clear_cache(server.id)
    return {"ok": True}


@router.post("/mcp/{server_id}/test", response_model=list[schemas.McpToolOut])
async def test_mcp_server(
    server_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    try:
        tools = await mcp_core.list_tools(server)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"连接失败：{exc}")
    return [
        schemas.McpToolOut(
            name=t["name"],
            description=t.get("description") or "",
            input_schema=t.get("input_schema") or {},
        )
        for t in tools
    ]


@router.post("/mcp/{server_id}/refresh", response_model=list[schemas.McpToolOut])
async def refresh_mcp_server(
    server_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    mcp_core.clear_cache(server.id)
    try:
        tools = await mcp_core.list_tools(server)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"连接失败：{exc}")
    return [
        schemas.McpToolOut(
            name=t["name"],
            description=t.get("description") or "",
            input_schema=t.get("input_schema") or {},
        )
        for t in tools
    ]
