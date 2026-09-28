from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .routers import (
    admin,
    auth,
    chat,
    conversations,
    dingtalk_bot,
    endpoints,
    feishu_bot,
    uploads,
    wecom_bot,
)
from .routers import mcp as mcp_router
from .routers import skills as skills_router
from .security import hash_password

Base.metadata.create_all(bind=engine)


def _ensure_columns() -> None:
    insp = inspect(engine)
    if "settings" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("settings")}
        if "logo_path" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE settings ADD COLUMN logo_path VARCHAR DEFAULT ''")
                )
        if "theme" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE settings ADD COLUMN theme VARCHAR DEFAULT 'warm'")
                )
        if "favicon_path" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE settings ADD COLUMN favicon_path VARCHAR DEFAULT ''"
                    )
                )
        if "site_title" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE settings ADD COLUMN site_title VARCHAR DEFAULT 'askai'"
                    )
                )
        if "debug_mode" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE settings ADD COLUMN debug_mode INTEGER DEFAULT 1")
                )
        with engine.begin() as conn:
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
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {name} {ddl}"))
        with engine.begin() as conn:
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
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {name} {ddl}"))
        search_settings = {
            "search_provider": "VARCHAR DEFAULT ''",
            "search_api_key": "VARCHAR DEFAULT ''",
            "search_base_url": "VARCHAR DEFAULT ''",
            "search_auto": "INTEGER DEFAULT 0",
        }
        for name, ddl in search_settings.items():
            if name not in cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {name} {ddl}"))
        dingtalk_settings = {
            "dingtalk_app_key": "VARCHAR DEFAULT ''",
            "dingtalk_app_secret": "VARCHAR DEFAULT ''",
            "dingtalk_agent_id": "VARCHAR DEFAULT ''",
            "dingtalk_redirect": "VARCHAR DEFAULT ''",
        }
        for name, ddl in dingtalk_settings.items():
            if name not in cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {name} {ddl}"))
        feishu_settings = {
            "feishu_app_id": "VARCHAR DEFAULT ''",
            "feishu_app_secret": "VARCHAR DEFAULT ''",
            "feishu_redirect": "VARCHAR DEFAULT ''",
        }
        for name, ddl in feishu_settings.items():
            if name not in cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {name} {ddl}"))
    if "users" in insp.get_table_names():
        ucols = {c["name"] for c in insp.get_columns("users")}
        for name, ddl in {
            "assistant_name": "VARCHAR DEFAULT ''",
            "assistant_avatar": "VARCHAR DEFAULT ''",
        }.items():
            if name not in ucols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
        if "dingtalk_userid" not in ucols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE users ADD COLUMN dingtalk_userid VARCHAR")
                )
        if "feishu_userid" not in ucols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN feishu_userid VARCHAR"))
    if "messages" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("messages")}
        if "tokens" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE messages ADD COLUMN tokens INTEGER DEFAULT 0")
                )
        if "endpoint_id" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE messages ADD COLUMN endpoint_id INTEGER")
                )
    if "conversations" in insp.get_table_names():
        ccols = {c["name"] for c in insp.get_columns("conversations")}
        if "bot_id" not in ccols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE conversations ADD COLUMN bot_id INTEGER")
                )
        if "mcp_ids" not in ccols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE conversations ADD COLUMN mcp_ids VARCHAR DEFAULT ''"
                    )
                )
        if "skill_ids" not in ccols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE conversations ADD COLUMN skill_ids VARCHAR DEFAULT ''"
                    )
                )
    if "knowledge_bases" in insp.get_table_names():
        kbcols = {c["name"] for c in insp.get_columns("knowledge_bases")}
        for name, ddl in {
            "provider": "VARCHAR DEFAULT 'dify'",
            "dataset_ids": "VARCHAR DEFAULT ''",
            "top_k": "INTEGER DEFAULT 5",
            "mode": "VARCHAR DEFAULT 'frontend'",
        }.items():
            if name not in kbcols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE knowledge_bases ADD COLUMN {name} {ddl}")
                    )
    if "wecom_bots" in insp.get_table_names():
        bcols = {c["name"] for c in insp.get_columns("wecom_bots")}
        if "provider" not in bcols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE wecom_bots ADD COLUMN provider VARCHAR DEFAULT 'wecom'"
                    )
                )
        if "mcp_ids" not in bcols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE wecom_bots ADD COLUMN mcp_ids VARCHAR DEFAULT ''")
                )
        if "skill_ids" not in bcols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE wecom_bots ADD COLUMN skill_ids VARCHAR DEFAULT ''"
                    )
                )


_ensure_columns()


def _seed_admin() -> None:
    db: Session = SessionLocal()
    try:
        from . import models

        if not db.query(models.Admin).first():
            db.add(
                models.Admin(username="admin", password_hash=hash_password("admin123"))
            )
            db.commit()
    finally:
        db.close()


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
app.include_router(admin.router, prefix="/api")
app.include_router(endpoints.router, prefix="/api")
app.include_router(wecom_bot.router, prefix="/api")
app.include_router(dingtalk_bot.router, prefix="/api")
app.include_router(feishu_bot.router, prefix="/api")
app.include_router(mcp_router.router, prefix="/api")
app.include_router(skills_router.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
