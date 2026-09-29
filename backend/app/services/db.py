"""多数据库支持：构建 SQLAlchemy URL / 连接参数、测试连接、检测驱动。

支持的数据库类型（``type`` 字段）：sqlite / mysql / postgresql / mssql / oracle。
应用通过 ``data/db_config.json`` 或环境变量 ``DATABASE_URL`` 决定使用哪个数据库。
"""

from __future__ import annotations

from urllib.parse import quote

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.engine import Engine

# 类型 -> SQLAlchemy 方言驱动
DIALECT_DRIVER = {
    "sqlite": "sqlite",
    "mysql": "mysql+pymysql",
    "postgresql": "postgresql+psycopg2",
    "mssql": "mssql+pymssql",
    "oracle": "oracle+oracledb",
}

# 方言 -> 需要检测的 Python 模块
DRIVER_MODULE = {
    "mysql": "pymysql",
    "postgresql": "psycopg2",
    "mssql": "pymssql",
    "oracle": "oracledb",
}

SUPPORTED_TYPES = list(DIALECT_DRIVER.keys())


def dialect_from_url(url: str) -> str:
    """从 SQLAlchemy URL 推断数据库类型。"""
    url = url or ""
    if url.startswith("sqlite"):
        return "sqlite"
    if url.startswith("mysql"):
        return "mysql"
    if url.startswith("postgres"):
        return "postgresql"
    if url.startswith("mssql"):
        return "mssql"
    if url.startswith("oracle"):
        return "oracle"
    return "sqlite"


def build_url(cfg: dict) -> tuple[str, str]:
    """根据配置字典构建 (sqlalchemy_url, dialect)。"""
    dtype = (cfg or {}).get("type") or "sqlite"
    dtype = dtype.lower()
    if dtype not in DIALECT_DRIVER:
        raise ValueError(f"不支持的数据库类型：{dtype}")
    if dtype == "sqlite":
        path = (cfg.get("path") or cfg.get("sqlite_path") or "./app.db").strip()
        url = f"sqlite:///{path}"
        return url, dtype
    host = (cfg.get("host") or "").strip()
    port = (cfg.get("port") or "").strip()
    database = (cfg.get("database") or cfg.get("dbname") or "").strip()
    username = (cfg.get("username") or "").strip()
    password = cfg.get("password") or ""
    driver = DIALECT_DRIVER[dtype]
    auth = ""
    if username:
        auth = f"{quote(username)}:{quote(password)}@"
    elif password:
        auth = f":{quote(password)}@"
    hostport = host
    if host and port:
        hostport = f"{host}:{port}"
    url = f"{driver}://{auth}{hostport}/{database}"
    return url, dtype


def build_connect_args(url: str) -> dict:
    """根据 URL 返回连接参数。"""
    url = url or ""
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if url.startswith("mysql"):
        return {"charset": "utf8mb4"}
    return {}


def create_engine(url: str) -> Engine:
    """创建 SQLAlchemy engine（惰性连接）。"""
    return sa_create_engine(
        url,
        connect_args=build_connect_args(url),
        pool_pre_ping=True,
    )


def test_connection(cfg: dict) -> dict:
    """测试目标数据库连接。返回 {ok, message, dialect}。"""
    dtype = (cfg or {}).get("type") or "sqlite"
    dtype = dtype.lower()
    try:
        url, dialect = build_url(cfg)
    except Exception as exc:
        return {"ok": False, "message": str(exc), "dialect": dtype}
    mod = DRIVER_MODULE.get(dtype)
    if mod:
        try:
            __import__(mod)
        except Exception as exc:
            return {
                "ok": False,
                "message": f"驱动 {mod} 未安装：{exc}",
                "dialect": dtype,
            }
    if dtype == "sqlite":
        # SQLite 本地文件仅验证可写路径
        import os

        path = (cfg.get("path") or cfg.get("sqlite_path") or "./app.db").strip()
        try:
            if path != ":memory:":
                parent = os.path.dirname(os.path.abspath(path)) or "."
                os.makedirs(parent, exist_ok=True)
                with open(path, "a"):
                    pass
        except Exception as exc:
            return {"ok": False, "message": f"SQLite 路径不可写：{exc}", "dialect": dtype}
        return {"ok": True, "message": "SQLite 路径有效", "dialect": dtype}
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            probe = "SELECT 1 FROM DUAL" if dialect == "oracle" else "SELECT 1"
            conn.exec_driver_sql(probe)
        engine.dispose()
        return {"ok": True, "message": "连接成功", "dialect": dtype}
    except Exception as exc:
        message = str(exc).strip() or exc.__class__.__name__
        return {"ok": False, "message": message, "dialect": dtype}


def driver_status() -> dict:
    """返回各数据库驱动的安装状态。"""
    result: dict[str, bool] = {}
    for dtype in SUPPORTED_TYPES:
        if dtype == "sqlite":
            result[dtype] = True
            continue
        mod = DRIVER_MODULE.get(dtype)
        if not mod:
            result[dtype] = False
            continue
        try:
            __import__(mod)
            result[dtype] = True
        except Exception:
            result[dtype] = False
    return result


def describe(dialect: str, cfg: dict | None = None) -> dict:
    """构造当前库的描述信息（脱敏）。"""
    cfg = cfg or {}
    if dialect == "sqlite":
        path = cfg.get("path") or cfg.get("sqlite_path") or "./app.db"
        return {"type": "sqlite", "database": path, "host": "", "port": ""}
    host = (cfg.get("host") or "").strip()
    port = (cfg.get("port") or "").strip()
    database = (cfg.get("database") or cfg.get("dbname") or "").strip()
    username = (cfg.get("username") or "").strip()
    return {
        "type": dialect,
        "database": database,
        "host": host,
        "port": port,
        "username": username,
    }
