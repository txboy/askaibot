import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import require_super
from app.database import get_db

router = APIRouter()
__all__ = ["export_audit_logs", "list_audit_logs"]


def _page(db: Session, page: int, size: int, action: str, target_type: str, admin: str, start: str, end: str):
    q = db.query(models.AuditLog)
    if action:
        q = q.filter(models.AuditLog.action == action)
    if target_type:
        q = q.filter(models.AuditLog.target_type == target_type)
    if admin:
        q = q.filter(models.AuditLog.admin_username == admin)
    if start:
        try:
            q = q.filter(models.AuditLog.created_at >= datetime.fromisoformat(start))
        except ValueError:
            pass
    if end:
        try:
            q = q.filter(models.AuditLog.created_at <= datetime.fromisoformat(end))
        except ValueError:
            pass
    total = q.count()
    rows = (
        q.order_by(models.AuditLog.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return total, [schemas.AuditLogOut.model_validate(r) for r in rows]


@router.get("/audit-logs", response_model=schemas.AuditPage)
def list_audit_logs(
    page: int = 1,
    size: int = 20,
    action: str = "",
    target_type: str = "",
    admin: str = "",
    start: str = "",
    end: str = "",
    _admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    total, items = _page(db, page, size, action, target_type, admin, start, end)
    return schemas.AuditPage(total=total, items=items)


@router.get("/audit-logs/export")
def export_audit_logs(
    action: str = "",
    target_type: str = "",
    admin: str = "",
    start: str = "",
    end: str = "",
    _admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    total, items = _page(db, 1, 100000, action, target_type, admin, start, end)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "admin", "role", "department_id", "action", "target_type", "target_id", "summary", "ip", "created_at"]
    )
    for it in items:
        writer.writerow(
            [
                it.id,
                it.admin_username,
                it.admin_role,
                it.department_id or "",
                it.action,
                it.target_type,
                it.target_id,
                it.summary,
                it.ip,
                it.created_at.isoformat() if it.created_at else "",
            ]
        )
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit_logs.csv"'},
    )
