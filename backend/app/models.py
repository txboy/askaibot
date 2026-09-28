from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nickname: Mapped[str] = mapped_column(String, default="用户")
    avatar: Mapped[str] = mapped_column(String, default="")
    assistant_name: Mapped[str] = mapped_column(String, default="")
    assistant_avatar: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    wecom_userid: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    bot_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, default="新对话")
    model: Mapped[str] = mapped_column(String, default="")
    mcp_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔的 MCP id
    skill_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔的 Skill id
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String, default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    endpoint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("api_endpoints.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    base_url: Mapped[str] = mapped_column(String, default="https://api.openai.com/v1")
    api_key: Mapped[str] = mapped_column(String, default="")
    default_model: Mapped[str] = mapped_column(String, default="gpt-4o-mini")
    wecom_corp_id: Mapped[str] = mapped_column(String, default="")
    wecom_secret: Mapped[str] = mapped_column(String, default="")
    wecom_agent_id: Mapped[str] = mapped_column(String, default="")
    wecom_redirect: Mapped[str] = mapped_column(String, default="")
    logo_path: Mapped[str] = mapped_column(String, default="")
    favicon_path: Mapped[str] = mapped_column(String, default="")
    site_title: Mapped[str] = mapped_column(String, default="askai")
    assistant_name: Mapped[str] = mapped_column(String, default="askai")
    assistant_avatar: Mapped[str] = mapped_column(String, default="")
    admin_secret_enabled: Mapped[int] = mapped_column(Integer, default=0)
    admin_secret: Mapped[str] = mapped_column(String, default="")
    theme: Mapped[str] = mapped_column(String, default="warm")
    debug_mode: Mapped[int] = mapped_column(Integer, default=1)
    sms_provider: Mapped[str] = mapped_column(String, default="")
    sms_access_key_id: Mapped[str] = mapped_column(String, default="")
    sms_secret: Mapped[str] = mapped_column(String, default="")
    sms_sign_name: Mapped[str] = mapped_column(String, default="")
    sms_template_code: Mapped[str] = mapped_column(String, default="")
    sms_region: Mapped[str] = mapped_column(String, default="")
    sms_sdk_app_id: Mapped[str] = mapped_column(String, default="")
    search_provider: Mapped[str] = mapped_column(String, default="")
    search_api_key: Mapped[str] = mapped_column(String, default="")
    search_base_url: Mapped[str] = mapped_column(String, default="")
    search_auto: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String, default="dify")  # dify / ragflow
    base_url: Mapped[str] = mapped_column(String)
    api_key: Mapped[str] = mapped_column(String, default="")
    dataset_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    mode: Mapped[str] = mapped_column(String, default="frontend")  # frontend / llm
    description: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WecomBot(Base):
    __tablename__ = "wecom_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    corp_id: Mapped[str] = mapped_column(String, default="")
    secret: Mapped[str] = mapped_column(String, default="")
    agent_id: Mapped[str] = mapped_column(String, default="")
    token: Mapped[str] = mapped_column(String, default="")
    aes_key: Mapped[str] = mapped_column(String, default="")
    kb_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    mcp_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    skill_ids: Mapped[str] = mapped_column(String, default="")  # 逗号分隔
    web_search: Mapped[int] = mapped_column(Integer, default=0)
    endpoint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("api_endpoints.id"), nullable=True
    )
    model: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=True, index=True
    )
    message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("messages.id"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String)
    stored_name: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String, default="")
    kind: Mapped[str] = mapped_column(String, default="text")  # image / text / doc
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    transport: Mapped[str] = mapped_column(String, default="http")  # http / stdio
    url: Mapped[str] = mapped_column(String, default="")
    headers: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    command: Mapped[str] = mapped_column(String, default="")
    args: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    env: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    mode: Mapped[str] = mapped_column(String, default="llm")  # llm / frontend
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    base_url: Mapped[str] = mapped_column(String)
    api_key: Mapped[str] = mapped_column(String, default="")
    models: Mapped[str] = mapped_column(Text, default="")  # 逗号/换行分隔的模型列表
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    dir_path: Mapped[str] = mapped_column(
        String, default=""
    )  # upload_dir 内的技能包目录
    content: Mapped[str] = mapped_column(
        Text, default=""
    )  # SKILL.md 正文（注入系统提示词）
    tools: Mapped[str] = mapped_column(Text, default="[]")  # JSON：工具声明列表
    scope: Mapped[str] = mapped_column(String, default="global")  # global / user
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SkillAccess(Base):
    __tablename__ = "skill_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
