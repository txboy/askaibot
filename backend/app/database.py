import json
import os
from urllib.parse import quote

from sqlalchemy.orm import declarative_base, sessionmaker

from . import config as app_config
from .services import db as db_service

Base = declarative_base()

_engine = None
_SessionLocal = None


def _default_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./data/app.db")


def resolve_config() -> dict | None:
    """读取 db_config.json；不存在或非法时返回 None。"""
    path = getattr(app_config.config, "db_config_file", "./data/db_config.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data.get("type"):
            return None
        return data
    except Exception:
        return None


def resolve_url() -> tuple[str, str]:
    """返回 (sqlalchemy_url, dialect)。

    优先级：db_config.json > DATABASE_URL 环境变量 > 默认 SQLite。
    """
    cfg = resolve_config()
    if cfg:
        return db_service.build_url(cfg)
    url = _default_url()
    return url, db_service.dialect_from_url(url)


def _init() -> None:
    global _engine, _SessionLocal
    url, _ = resolve_url()
    _engine = db_service.create_engine(url)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


_init()


def get_engine():
    return _engine


def get_sessionlocal():
    return _SessionLocal


def current_db_info() -> dict:
    """返回当前数据库的描述信息（脱敏），供管理后台展示。"""
    cfg = resolve_config()
    _, dialect = resolve_url()
    return db_service.describe(dialect, cfg)


def reconfigure(cfg: dict) -> dict:
    """根据配置字典重新初始化 engine / sessionmaker（热切换）。"""
    global _engine, _SessionLocal
    url, dialect = db_service.build_url(cfg)
    new_engine = db_service.create_engine(url)
    new_session = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)
    old_engine = _engine
    _engine = new_engine
    _SessionLocal = new_session
    if old_engine is not None:
        try:
            old_engine.dispose()
        except Exception:
            pass
    redacted = url
    if cfg.get("password"):
        redacted = url.replace(quote(cfg["password"]), "****")
    return {"url": redacted, "dialect": dialect}


def save_config(cfg: dict) -> str:
    """将配置持久化到 db_config.json，返回文件路径。"""
    path = getattr(app_config.config, "db_config_file", "./data/db_config.json")
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return path


def get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
