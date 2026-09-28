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

router = APIRouter()
__all__ = ["create_skill", "delete_skill", "list_skills", "test_skill", "update_skill"]

def _skill_out(skill: models.Skill, db: Session) -> schemas.SkillOut:
    try:
        tools = json.loads(skill.tools or "[]")
    except Exception:
        tools = []
    if not isinstance(tools, list):
        tools = []
    user_ids = [
        a.user_id
        for a in db.query(models.SkillAccess)
        .filter(models.SkillAccess.skill_id == skill.id)
        .all()
    ]
    return schemas.SkillOut(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        scope=skill.scope,
        enabled=skill.enabled,
        tools=[
            schemas.SkillToolOut(
                name=t.get("name", ""),
                description=t.get("description") or "",
                command=t.get("command") or "",
                input_schema=t.get("input_schema") or {},
            )
            for t in tools
        ],
        user_ids=user_ids,
    )

@router.get("/skills", response_model=list[schemas.SkillOut])
def list_skills(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_skill_out(s, db) for s in db.query(models.Skill).all()]

@router.post("/skills", response_model=schemas.SkillOut)
async def create_skill(
    file: UploadFile = File(...),
    scope: str = Form("global"),
    enabled: int = Form(1),
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if scope not in ("global", "user"):
        scope = "global"
    skills_base = os.path.join(config.upload_dir, "skills")
    os.makedirs(skills_base, exist_ok=True)
    tmp_zip = os.path.join(skills_base, f"_upload_{uuid.uuid4().hex}.zip")
    tmp_dir = os.path.join(skills_base, f".tmp_{uuid.uuid4().hex}")
    try:
        content = await file.read()
        with open(tmp_zip, "wb") as fh:
            fh.write(content)
        try:
            skill_core.extract_upload(tmp_zip, tmp_dir)
            info = skill_core.parse_skill(tmp_dir)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"技能包解析失败：{exc}")
        skill = models.Skill(
            name=info["name"],
            description=info["description"],
            dir_path=tmp_dir,
            content=info["content"],
            tools=json.dumps(info["tools"], ensure_ascii=False),
            scope=scope,
            enabled=enabled,
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)
        final_dir = os.path.join(skills_base, str(skill.id))
        if os.path.isdir(final_dir):
            shutil.rmtree(final_dir, ignore_errors=True)
        shutil.move(tmp_dir, final_dir)
        tmp_dir = final_dir
        skill.dir_path = final_dir
        db.commit()
        db.refresh(skill)
        return _skill_out(skill, db)
    finally:
        if os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except OSError:
                pass
        if os.path.isdir(tmp_dir) and not os.path.exists(
            os.path.join(tmp_dir, "SKILL.md")
        ):
            shutil.rmtree(tmp_dir, ignore_errors=True)

@router.put("/skills/{skill_id}", response_model=schemas.SkillOut)
def update_skill(
    skill_id: int,
    payload: schemas.SkillUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    skill = db.get(models.Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    if payload.name is not None:
        skill.name = payload.name
    if payload.description is not None:
        skill.description = payload.description
    if payload.scope is not None:
        if payload.scope not in ("global", "user"):
            raise HTTPException(status_code=400, detail="scope 仅支持 global/user")
        skill.scope = payload.scope
    if payload.enabled is not None:
        skill.enabled = payload.enabled
    if payload.user_ids is not None:
        db.query(models.SkillAccess).filter(
            models.SkillAccess.skill_id == skill.id
        ).delete()
        for uid in payload.user_ids:
            db.add(models.SkillAccess(skill_id=skill.id, user_id=uid))
    db.commit()
    db.refresh(skill)
    return _skill_out(skill, db)

@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    skill = db.get(models.Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    if skill.dir_path:
        shutil.rmtree(skill.dir_path, ignore_errors=True)
    db.query(models.SkillAccess).filter(
        models.SkillAccess.skill_id == skill.id
    ).delete()
    db.delete(skill)
    db.commit()
    return {"ok": True}

@router.post("/skills/{skill_id}/test")
async def test_skill(
    skill_id: int,
    payload: schemas.SkillTestRequest,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    skill = db.get(models.Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    try:
        tools = json.loads(skill.tools or "[]")
    except Exception:
        tools = []
    if not isinstance(tools, list):
        tools = []
    tool = next(
        (t for t in tools if isinstance(t, dict) and t.get("name") == payload.tool),
        None,
    )
    if not tool:
        raise HTTPException(status_code=400, detail=f"技能中不存在工具：{payload.tool}")
    try:
        output = await skill_core.call_tool(skill, tool, payload.args or {})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"执行失败：{exc}")
    return {"output": output}