from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import config
from .database import get_db
from . import models

security = HTTPBearer()


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.jwt_expire_minutes),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def create_admin_token(username: str, role: str = "super", department_id: int | None = None) -> str:
    payload = {
        "sub": username,
        "role": role,
        "department_id": department_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.jwt_expire_minutes),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
        )


def decode_token(token: str) -> int:
    payload = _decode(token)
    return int(payload["sub"])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.User:
    user_id = decode_token(credentials.credentials)
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.Admin:
    payload = _decode(credentials.credentials)
    if payload.get("role") not in ("super", "dept"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要管理员权限")
    admin = (
        db.query(models.Admin)
        .filter(models.Admin.username == payload["sub"])
        .first()
    )
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员不存在")
    return admin


def require_super(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.Admin:
    admin = get_current_admin(credentials=credentials, db=db)
    if admin.role != "super":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限"
        )
    return admin


def require_dept(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.Admin:
    admin = get_current_admin(credentials=credentials, db=db)
    if admin.role != "dept" or not admin.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要部门管理员权限"
        )
    return admin
