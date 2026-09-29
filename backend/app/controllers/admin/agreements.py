from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import require_super
from app.database import get_db
from app.services.audit import audit

router = APIRouter()
__all__ = ["create_agreement", "delete_agreement", "list_agreements", "update_agreement"]


@router.get("/agreements", response_model=list[schemas.AgreementOut])
def list_agreements(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Agreement)
        .order_by(models.Agreement.id.desc())
        .all()
    )


@router.post("/agreements", response_model=schemas.AgreementOut)
def create_agreement(
    payload: schemas.AgreementCreate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    agreement = models.Agreement(
        title=payload.title,
        content=payload.content or "",
        enabled=payload.enabled,
        required=payload.required,
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)
    audit(
        db,
        admin,
        action="agreement.create",
        target_type="agreement",
        target_id=agreement.id,
        summary=f"创建协议 {agreement.title}",
    )
    db.commit()
    return agreement


@router.put("/agreements/{agreement_id}", response_model=schemas.AgreementOut)
def update_agreement(
    agreement_id: int,
    payload: schemas.AgreementUpdate,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    agreement = db.get(models.Agreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail="协议不存在")
    if payload.title is not None:
        agreement.title = payload.title
    if payload.content is not None:
        agreement.content = payload.content
    if payload.enabled is not None:
        agreement.enabled = payload.enabled
    if payload.required is not None:
        agreement.required = payload.required
    db.commit()
    db.refresh(agreement)
    audit(
        db,
        admin,
        action="agreement.update",
        target_type="agreement",
        target_id=agreement.id,
        summary=f"更新协议 {agreement.title}",
    )
    db.commit()
    return agreement


@router.delete("/agreements/{agreement_id}")
def delete_agreement(
    agreement_id: int,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    agreement = db.get(models.Agreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail="协议不存在")
    audit(
        db,
        admin,
        action="agreement.delete",
        target_type="agreement",
        target_id=agreement.id,
        summary=f"删除协议 {agreement.title}",
    )
    db.delete(agreement)
    db.commit()
    return {"ok": True}
