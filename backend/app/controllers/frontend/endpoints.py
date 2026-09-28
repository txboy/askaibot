from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.common import parse_models
from app.database import get_db

router = APIRouter(tags=["endpoints"])


@router.get("/knowledge-bases", response_model=list[schemas.KnowledgeBasePublic])
def list_public_knowledge_bases(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    kbs = (
        db.query(models.KnowledgeBase)
        .filter(
            models.KnowledgeBase.enabled == 1,
            models.KnowledgeBase.mode == "frontend",
        )
        .order_by(models.KnowledgeBase.id.asc())
        .all()
    )
    return [
        schemas.KnowledgeBasePublic(
            id=kb.id, name=kb.name, provider=kb.provider, description=kb.description
        )
        for kb in kbs
    ]


@router.get("/endpoints", response_model=list[schemas.EndpointPublic])
def list_public_endpoints(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    endpoints = (
        db.query(models.ApiEndpoint)
        .filter(models.ApiEndpoint.enabled == 1)
        .order_by(models.ApiEndpoint.is_default.desc(), models.ApiEndpoint.id.asc())
        .all()
    )
    return [
        schemas.EndpointPublic(
            id=e.id,
            name=e.name,
            base_url=e.base_url,
            models=parse_models(e.models),
            is_default=e.is_default,
        )
        for e in endpoints
    ]
