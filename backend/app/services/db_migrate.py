"""数据库迁移与切换。

将当前数据库（源）的数据完整迁移到目标数据库，并完成热切换。
迁移全程使用独立 engine，不动当前在线的源 engine；成功后由调用方
持久化配置并热切换。

特性：
- 目标库先用 ``Base.metadata.create_all`` 建表（幂等）。
- 按外键依赖顺序逐表拷贝，保留主键。
- 非覆盖模式下，若目标库已有非空同名表则拒绝。
- 覆盖模式下，先 ``drop_all`` 再重建。
- MSSQL 插入前启用 ``IDENTITY_INSERT``；Oracle 迁后重设 sequence。
"""

from __future__ import annotations

import os
import shutil
import time
from sqlalchemy import func, inspect, select
from sqlalchemy.engine import Engine

from .. import models  # noqa: F401  （注册模型到 Base.metadata）
from ..database import Base
from . import db as db_service


def backup_sqlite(src_url) -> dict:
    """备份 SQLite 数据库文件到 data/backups/，返回备份信息。"""
    path = getattr(src_url, "database", None)
    if not path or path == ":memory:" or not os.path.exists(path):
        return {"ok": False, "message": "当前库非 SQLite 文件，无法自动备份"}
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(path)), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, f"app_{stamp}.db")
    shutil.copy2(path, dest)
    return {"ok": True, "message": f"已备份到 {dest}", "path": dest}


def _dependency_order(metadata) -> list[str]:
    """按外键依赖拓扑排序表名（被引用表在前）。"""
    tables = list(metadata.tables.values())
    deps: dict[str, set[str]] = {}
    for t in tables:
        deps[t.name] = set()
        for fk in t.foreign_keys:
            ref = fk.column.table.name
            if ref != t.name:
                deps[t.name].add(ref)
    order: list[str] = []
    remaining = {name for name in deps}
    while remaining:
        ready = [name for name in remaining if not (deps[name] & remaining)]
        if not ready:
            ready = [next(iter(remaining))]
        for name in ready:
            remaining.discard(name)
            order.append(name)
    return order


def _reset_oracle_sequences(target_conn, metadata, oracle_dialect) -> None:
    """迁后尽力重设 Oracle 自增 sequence 到 max(id)+1。"""
    try:
        for table_name, table in metadata.tables.items():
            for col in table.columns:
                if col.primary_key and getattr(col, "autoincrement", False):
                    seq_candidates = [
                        f"{table_name}_id_seq",
                        f"{table_name}_seq",
                        f"{table_name}_{col.name}_seq",
                    ]
                    for seq in seq_candidates:
                        try:
                            max_id = target_conn.execute(
                                select(func.max(col)).select_from(table)
                            ).scalar()
                            if max_id is None:
                                continue
                            target_conn.exec_driver_sql(
                                f"ALTER SEQUENCE {seq} RESTART START WITH {int(max_id) + 1}"
                            )
                            break
                        except Exception:
                            continue
    except Exception:
        pass


def _table_has_rows(target_conn, table) -> bool:
    try:
        return bool(
            target_conn.execute(select(func.count()).select_from(table)).scalar()
        )
    except Exception:
        return False


def migrate(
    cfg: dict,
    override: bool = False,
    backup: bool = True,
    src_engine: Engine | None = None,
) -> dict:
    """把当前库数据迁移到目标库（cfg），返回描述信息。

    不改动当前在线的源 engine；调用方负责后续持久化与热切换。
    """
    src_engine = src_engine or None
    if src_engine is None:
        from ..database import get_engine

        src_engine = get_engine()

    target_url, dialect = db_service.build_url(cfg)
    target_engine = db_service.create_engine(target_url)

    result = {
        "ok": False,
        "target_url_redacted": _redact_url(target_url),
        "dialect": dialect,
    }

    # 备份（可选）
    bk = None
    if backup:
        try:
            bk = backup_sqlite(getattr(src_engine, "url", None))
        except Exception:
            bk = {"ok": False, "message": "备份失败"}

    metadata = Base.metadata
    insp = inspect(target_engine)

    with src_engine.connect() as src_conn:
        with target_engine.connect() as target_conn:
            try:
                # 覆盖模式：清空目标库重建
                if override:
                    Base.metadata.drop_all(target_engine)
                    Base.metadata.create_all(target_engine)
                else:
                    Base.metadata.create_all(target_engine)
                    existing = set(insp.get_table_names())
                    for table_name in existing & set(metadata.tables.keys()):
                        if _table_has_rows(target_conn, metadata.tables[table_name]):
                            result["message"] = (
                                f"目标库已存在非空表 {table_name}，需确认覆盖"
                            )
                            result["backup"] = bk
                            return result

                for table_name in _dependency_order(metadata):
                    table = metadata.tables[table_name]
                    rows = src_conn.execute(select(table)).mappings().all()
                    if not rows:
                        continue
                    if dialect == "mssql":
                        target_conn.exec_driver_sql(
                            f"SET IDENTITY_INSERT {table_name} ON"
                        )
                    target_conn.execute(table.insert(), [dict(r) for r in rows])
                    if dialect == "mssql":
                        target_conn.exec_driver_sql(
                            f"SET IDENTITY_INSERT {table_name} OFF"
                        )
                if dialect == "oracle":
                    _reset_oracle_sequences(target_conn, metadata, dialect)
                target_conn.commit()
            except Exception as exc:
                target_conn.rollback()
                result["message"] = f"迁移失败：{exc}"
                result["backup"] = bk
                return result

    target_engine.dispose()
    result["ok"] = True
    result["message"] = "迁移成功"
    result["backup"] = bk
    return result


def _redact_url(url: str) -> str:
    """隐藏 URL 中的密码。"""
    if "://" in url and "@" in url:
        scheme, rest = url.split("://", 1)
        userinfo, _h = rest.split("@", 1)
        if ":" in userinfo:
            userinfo = userinfo.split(":", 1)[0] + ":****"
        return f"{scheme}://{userinfo}@{_h}"
    return url
