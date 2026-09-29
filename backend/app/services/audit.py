from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app import models


def audit(
    db: Session,
    admin: Optional[models.Admin] = None,
    action: str = "",
    target_type: str = "",
    target_id: int = 0,
    summary: str = "",
    ip: str = "",
    user_agent: str = "",
) -> models.AuditLog:
    """记录一条关键操作审计日志（写入后由调用方负责 db.commit()）。"""
    record = models.AuditLog(
        admin_id=admin.id if admin else None,
        admin_username=admin.username if admin else "",
        admin_role=getattr(admin, "role", "") if admin else "",
        department_id=getattr(admin, "department_id", None) if admin else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(record)
    return record
