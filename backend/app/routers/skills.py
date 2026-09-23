import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import skills as skill_core
from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[schemas.SkillPublic])
async def list_my_skills(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回当前用户可用的技能（global + 分配给本用户）。"""
    skills = skill_core.user_skills(db, user.id)
    out: list[schemas.SkillPublic] = []
    for s in skills:
        try:
            tools = json.loads(s.tools or "[]")
        except Exception:
            tools = []
        if not isinstance(tools, list):
            tools = []
        out.append(
            schemas.SkillPublic(
                id=s.id,
                name=s.name,
                description=s.description,
                tools=[
                    schemas.SkillToolOut(
                        name=t.get("name", ""),
                        description=t.get("description") or "",
                        command=t.get("command") or "",
                        input_schema=t.get("input_schema") or {},
                    )
                    for t in tools
                ],
            )
        )
    return out
