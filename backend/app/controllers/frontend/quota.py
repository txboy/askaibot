from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import quota as quota_core

router = APIRouter(tags=["quota"])


@router.get("/quota", response_model=schemas.QuotaInfo)
def get_quota(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return quota_core.token_limit_status(db, user)
