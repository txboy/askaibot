from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import Base, get_engine, get_sessionlocal
from .controllers.admin import router as admin_router
from .controllers.frontend import (
    auth,
    chat,
    conversations,
    endpoints,
    mcp,
    quota,
    skills,
    uploads,
)
from .controllers.webhook import dingtalk_bot, feishu_bot, wecom_bot
from .security import hash_password


def _add_column(conn, table: str, column: str, definition: str) -> None:
    """按方言追加列：SQLite/MySQL/PostgreSQL 用 ADD COLUMN，MSSQL/Oracle 用 ADD。"""
    dialect = conn.dialect.name if hasattr(conn, "dialect") else ""
    if dialect in ("mssql", "oracle"):
        conn.execute(text(f"ALTER TABLE {table} ADD {column} {definition}"))
    else:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def _ensure_columns(engine) -> None:
    insp = inspect(engine)
    if "settings" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("settings")}
        with engine.begin() as conn:
            if "logo_path" not in cols:
                _add_column(conn, "settings", "logo_path", "VARCHAR DEFAULT ''")
            if "theme" not in cols:
                _add_column(conn, "settings", "theme", "VARCHAR DEFAULT 'warm'")
            if "favicon_path" not in cols:
                _add_column(conn, "settings", "favicon_path", "VARCHAR DEFAULT ''")
            if "site_title" not in cols:
                _add_column(conn, "settings", "site_title", "VARCHAR DEFAULT 'askai'")
            if "debug_mode" not in cols:
                _add_column(conn, "settings", "debug_mode", "INTEGER DEFAULT 1")
            conn.execute(
                text("UPDATE settings SET site_title = 'askai' WHERE site_title = ''")
            )
            for name, ddl in {
                "admin_secret_enabled": "INTEGER DEFAULT 0",
                "admin_secret": "VARCHAR DEFAULT ''",
                "assistant_name": "VARCHAR DEFAULT 'askai'",
                "assistant_avatar": "VARCHAR DEFAULT ''",
            }.items():
                if name not in cols:
                    _add_column(conn, "settings", name, ddl)
            conn.execute(
                text(
                    "UPDATE settings SET assistant_name = 'askai' WHERE assistant_name = ''"
                )
            )
            extra_settings = {
                "sms_provider": "VARCHAR DEFAULT ''",
                "sms_access_key_id": "VARCHAR DEFAULT ''",
                "sms_secret": "VARCHAR DEFAULT ''",
                "sms_sign_name": "VARCHAR DEFAULT ''",
                "sms_template_code": "VARCHAR DEFAULT ''",
                "sms_region": "VARCHAR DEFAULT ''",
                "sms_sdk_app_id": "VARCHAR DEFAULT ''",
                "sms_captcha_enabled": "INTEGER DEFAULT 1",
                "sms_captcha_provider": "VARCHAR DEFAULT 'builtin'",
                "sms_cooldown": "INTEGER DEFAULT 60",
                "geetest_captcha_id": "VARCHAR DEFAULT ''",
                "geetest_captcha_key": "VARCHAR DEFAULT ''",
                "tencent_captcha_app_id": "VARCHAR DEFAULT ''",
                "tencent_captcha_app_secret_key": "VARCHAR DEFAULT ''",
                "aliyun_captcha_access_key_id": "VARCHAR DEFAULT ''",
                "aliyun_captcha_access_key_secret": "VARCHAR DEFAULT ''",
                "aliyun_captcha_scene_id": "VARCHAR DEFAULT ''",
            }
            for name, ddl in extra_settings.items():
                if name not in cols:
                    _add_column(conn, "settings", name, ddl)
            search_settings = {
                "search_provider": "VARCHAR DEFAULT ''",
                "search_api_key": "VARCHAR DEFAULT ''",
                "search_base_url": "VARCHAR DEFAULT ''",
                "search_auto": "INTEGER DEFAULT 0",
                "search_scope": "VARCHAR DEFAULT 'global'",
            }
            for name, ddl in search_settings.items():
                if name not in cols:
                    _add_column(conn, "settings", name, ddl)
            if "token_limit_daily" not in cols:
                _add_column(conn, "settings", "token_limit_daily", "INTEGER")
            system_prompt_settings = {
                "system_prompt": "TEXT DEFAULT ''",
                "wecom_system_prompt": "TEXT DEFAULT ''",
                "dingtalk_system_prompt": "TEXT DEFAULT ''",
                "feishu_system_prompt": "TEXT DEFAULT ''",
            }
            for name, ddl in system_prompt_settings.items():
                if name not in cols:
                    _add_column(conn, "settings", name, ddl)
            dingtalk_settings = {
                "dingtalk_app_key": "VARCHAR DEFAULT ''",
                "dingtalk_app_secret": "VARCHAR DEFAULT ''",
                "dingtalk_agent_id": "VARCHAR DEFAULT ''",
                "dingtalk_redirect": "VARCHAR DEFAULT ''",
            }
            for name, ddl in dingtalk_settings.items():
                if name not in cols:
                    _add_column(conn, "settings", name, ddl)
            feishu_settings = {
                "feishu_app_id": "VARCHAR DEFAULT ''",
                "feishu_app_secret": "VARCHAR DEFAULT ''",
                "feishu_redirect": "VARCHAR DEFAULT ''",
            }
            for name, ddl in feishu_settings.items():
                if name not in cols:
                    _add_column(conn, "settings", name, ddl)
    if "users" in insp.get_table_names():
        ucols = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            for name, ddl in {
                "assistant_name": "VARCHAR DEFAULT ''",
                "assistant_avatar": "VARCHAR DEFAULT ''",
            }.items():
                if name not in ucols:
                    _add_column(conn, "users", name, ddl)
            if "dingtalk_userid" not in ucols:
                _add_column(conn, "users", "dingtalk_userid", "VARCHAR")
            if "feishu_userid" not in ucols:
                _add_column(conn, "users", "feishu_userid", "VARCHAR")
            if "agreed_agreement_ids" not in ucols:
                _add_column(conn, "users", "agreed_agreement_ids", "VARCHAR DEFAULT ''")
            if "agreed_at" not in ucols:
                _add_column(conn, "users", "agreed_at", "DATETIME")
            if "department_id" not in ucols:
                _add_column(conn, "users", "department_id", "INTEGER")
            if "token_limit_daily" not in ucols:
                _add_column(conn, "users", "token_limit_daily", "INTEGER")
    if "admins" in insp.get_table_names():
        acols = {c["name"] for c in insp.get_columns("admins")}
        with engine.begin() as conn:
            if "role" not in acols:
                _add_column(conn, "admins", "role", "VARCHAR DEFAULT 'super'")
            if "department_id" not in acols:
                _add_column(conn, "admins", "department_id", "INTEGER")
    if "departments" in insp.get_table_names():
        dcols = {c["name"] for c in insp.get_columns("departments")}
        with engine.begin() as conn:
            if "token_limit_daily" not in dcols:
                _add_column(conn, "departments", "token_limit_daily", "INTEGER")
    if "messages" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("messages")}
        with engine.begin() as conn:
            if "tokens" not in cols:
                _add_column(conn, "messages", "tokens", "INTEGER DEFAULT 0")
            if "endpoint_id" not in cols:
                _add_column(conn, "messages", "endpoint_id", "INTEGER")
    if "conversations" in insp.get_table_names():
        ccols = {c["name"] for c in insp.get_columns("conversations")}
        with engine.begin() as conn:
            if "bot_id" not in ccols:
                _add_column(conn, "conversations", "bot_id", "INTEGER")
            if "mcp_ids" not in ccols:
                _add_column(conn, "conversations", "mcp_ids", "VARCHAR DEFAULT ''")
            if "skill_ids" not in ccols:
                _add_column(conn, "conversations", "skill_ids", "VARCHAR DEFAULT ''")
    if "knowledge_bases" in insp.get_table_names():
        kbcols = {c["name"] for c in insp.get_columns("knowledge_bases")}
        with engine.begin() as conn:
            for name, ddl in {
                "provider": "VARCHAR DEFAULT 'dify'",
                "dataset_ids": "VARCHAR DEFAULT ''",
                "top_k": "INTEGER DEFAULT 5",
                "mode": "VARCHAR DEFAULT 'frontend'",
                "scope": "VARCHAR DEFAULT 'global'",
            }.items():
                if name not in kbcols:
                    _add_column(conn, "knowledge_bases", name, ddl)
    if "api_endpoints" in insp.get_table_names():
        ecols = {c["name"] for c in insp.get_columns("api_endpoints")}
        with engine.begin() as conn:
            if "scope" not in ecols:
                _add_column(conn, "api_endpoints", "scope", "VARCHAR DEFAULT 'global'")
            if "system_prompt" not in ecols:
                _add_column(conn, "api_endpoints", "system_prompt", "TEXT DEFAULT ''")
    if "mcp_servers" in insp.get_table_names():
        mcols = {c["name"] for c in insp.get_columns("mcp_servers")}
        with engine.begin() as conn:
            if "scope" not in mcols:
                _add_column(conn, "mcp_servers", "scope", "VARCHAR DEFAULT 'global'")
    if "skills" in insp.get_table_names():
        scols = {c["name"] for c in insp.get_columns("skills")}
        with engine.begin() as conn:
            if "scope" not in scols:
                _add_column(conn, "skills", "scope", "VARCHAR DEFAULT 'global'")
    if "wecom_bots" in insp.get_table_names():
        bcols = {c["name"] for c in insp.get_columns("wecom_bots")}
        with engine.begin() as conn:
            if "provider" not in bcols:
                _add_column(conn, "wecom_bots", "provider", "VARCHAR DEFAULT 'wecom'")
            if "mcp_ids" not in bcols:
                _add_column(conn, "wecom_bots", "mcp_ids", "VARCHAR DEFAULT ''")
            if "skill_ids" not in bcols:
                _add_column(conn, "wecom_bots", "skill_ids", "VARCHAR DEFAULT ''")
            if "system_prompt" not in bcols:
                _add_column(conn, "wecom_bots", "system_prompt", "TEXT DEFAULT ''")


def _ensure_oracle_identity(engine) -> None:
    """Oracle：把老 schema 的整型主键列补成 identity，并把序列推进到 max+1。

    旧版本 ``create_all`` 生成的 Oracle 主键为纯 ``INTEGER NOT NULL``（无 identity），
    显式插入时 ``RETURNING id`` 会得到 NULL（ORA-01400）。启动/切换后对每个
    配置了 ``Identity()`` 的主键列，若当前列还不是 identity，则转为
    ``GENERATED BY DEFAULT AS IDENTITY`` 并 RESTART 到 max(id)+1。
    仅对 Oracle 生效，其余方言直接返回。
    """
    if engine.dialect.name != "oracle":
        return
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    try:
        with engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                if table_name not in tables:
                    continue
                for col in table.columns:
                    if not col.primary_key or getattr(col, "identity", None) is None:
                        continue
                    try:
                        row = conn.execute(
                            text(
                                "SELECT identity_column FROM user_tab_columns "
                                "WHERE UPPER(table_name) = UPPER(:t) "
                                "AND UPPER(column_name) = UPPER(:c)"
                            ),
                            {"t": table_name, "c": col.name},
                        ).first()
                    except Exception:
                        continue
                    if row and row[0] == "YES":
                        continue
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE {table_name} MODIFY ({col.name} "
                                f"GENERATED BY DEFAULT AS IDENTITY)"
                            )
                        )
                        print(
                            f"[schema] oracle identity: {table_name}.{col.name} -> identity",
                            flush=True,
                        )
                    except Exception as exc:
                        print(
                            f"[schema] oracle identity 失败: {table_name}.{col.name}: {exc}",
                            flush=True,
                        )
                        continue
                    try:
                        max_id = conn.execute(
                            text(f"SELECT MAX({col.name}) FROM {table_name}")
                        ).scalar()
                    except Exception:
                        max_id = None
                    if max_id is not None:
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE {table_name} MODIFY ({col.name} "
                                    f"GENERATED BY DEFAULT AS IDENTITY "
                                    f"(RESTART START WITH {int(max_id) + 1}))"
                                )
                            )
                            print(
                                f"[schema] oracle identity restart: {table_name}.{col.name} -> {int(max_id) + 1}",
                                flush=True,
                            )
                        except Exception as exc:
                            print(
                                f"[schema] oracle identity restart 失败: {table_name}.{col.name}: {exc}",
                                flush=True,
                            )
    except Exception:
        pass


def recreate_schema(bind_engine) -> None:
    """幂等建表 + 补列 + Oracle 自增修复（用于启动与数据库切换后）。"""
    Base.metadata.create_all(bind=bind_engine)
    _ensure_columns(bind_engine)
    _ensure_oracle_identity(bind_engine)


def setup_database() -> None:
    """初始化当前数据库（仅当连接到的库已就绪时）。"""
    recreate_schema(get_engine())


def _seed_admin() -> None:
    db: Session = get_sessionlocal()()
    try:
        from . import models

        if not db.query(models.Admin).first():
            db.add(
                models.Admin(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role="super",
                )
            )
            db.commit()
    finally:
        db.close()


setup_database()
_seed_admin()

app = FastAPI(title="聊天机器人")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(endpoints.router, prefix="/api")
app.include_router(wecom_bot.router, prefix="/api")
app.include_router(dingtalk_bot.router, prefix="/api")
app.include_router(feishu_bot.router, prefix="/api")
app.include_router(mcp.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(quota.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
