from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import require_super
from app.database import (
    current_db_info,
    get_db,
    get_engine,
    reconfigure,
    resolve_config,
    save_config,
)
from app.services import db as db_service
from app.services import db_migrate
from app.services.audit import audit

router = APIRouter()
__all__ = [
    "admin_db",
    "admin_db_test",
    "admin_db_switch",
    "admin_db_backup",
]


def _validate_cfg(cfg: schemas.DbConfigIn) -> dict:
    dtype = (cfg.type or "").lower()
    if dtype not in db_service.SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的数据库类型：{cfg.type}")
    data = {
        "type": dtype,
        "path": cfg.path,
        "host": cfg.host,
        "port": cfg.port,
        "database": cfg.database,
        "username": cfg.username,
        "password": cfg.password,
    }
    return data


@router.get("/db", response_model=schemas.DbInfoOut)
def admin_db(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    info = current_db_info()
    return schemas.DbInfoOut(
        type=info.get("type", "sqlite"),
        database=info.get("database", ""),
        host=info.get("host", ""),
        port=info.get("port", ""),
        username=info.get("username", ""),
        configured=resolve_config() is not None,
        drivers=db_service.driver_status(),
    )


@router.post("/db/test", response_model=schemas.DbTestResult)
def admin_db_test(
    payload: schemas.DbConfigIn,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    cfg = _validate_cfg(payload)
    result = db_service.test_connection(cfg)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return schemas.DbTestResult(ok=True, message=result["message"], dialect=result["dialect"])


@router.post("/db/switch", response_model=schemas.DbSwitchResult)
def admin_db_switch(
    payload: schemas.DbConfigIn,
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    cfg = _validate_cfg(payload)
    # 切换前测试连接
    conn = db_service.test_connection(cfg)
    if not conn["ok"]:
        raise HTTPException(status_code=400, detail=f"目标数据库不可用：{conn['message']}")
    # 迁移数据
    result = db_migrate.migrate(cfg, override=bool(payload.override), backup=True)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])
    # 持久化配置 + 热切换
    save_config(cfg)
    switched = reconfigure(cfg)
    # 切换后确保 schema 就绪
    try:
        from app.main import recreate_schema

        recreate_schema(get_engine())
    except Exception:
        pass
    audit(
        db,
        admin,
        action="db.switch",
        target_type="database",
        target_id=0,
        summary=f"数据库切换至 {switched['dialect']}",
    )
    db.commit()
    return schemas.DbSwitchResult(
        ok=True,
        message="迁移并切换成功",
        dialect=switched["dialect"],
        backup=result.get("backup"),
    )


@router.post("/db/backup", response_model=schemas.DbBackupResult)
def admin_db_backup(
    admin: models.Admin = Depends(require_super),
    db: Session = Depends(get_db),
):
    result = db_migrate.backup_sqlite(get_engine().url)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return schemas.DbBackupResult(ok=True, message=result["message"], path=result.get("path", ""))
