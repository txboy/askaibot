import json
import os
import shutil
import uuid
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
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
from app.services.audit import audit

router = APIRouter()
__all__ = ["admin_login", "admin_me"]


@router.post("/login", response_model=schemas.AdminLoginResponse)
def admin_login(
    payload: schemas.AdminLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = (
        db.query(models.Admin).filter(models.Admin.username == payload.username).first()
    )
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    ip = request.client.host if request.client else ""
    audit(
        db,
        admin,
        action="auth.login",
        target_type="admin",
        target_id=admin.id,
        summary=f"管理员登录 {admin.username}",
        ip=ip,
        user_agent=request.headers.get("user-agent", ""),
    )
    db.commit()
    return schemas.AdminLoginResponse(
        token=create_admin_token(admin.username, admin.role, admin.department_id)
    )


@router.get("/me", response_model=schemas.AdminMe)
def admin_me(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    department_name = None
    if admin.department_id:
        d = db.get(models.Department, admin.department_id)
        department_name = d.name if d else None
    return schemas.AdminMe(
        username=admin.username,
        role=admin.role,
        department_id=admin.department_id,
        department_name=department_name,
    )