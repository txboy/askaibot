from sqlalchemy import Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .types import OrEmptyStr, OrEmptyText
from ..database import Base


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    base_url: Mapped[str] = mapped_column(
        String(500), default="https://api.openai.com/v1"
    )
    api_key: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    default_model: Mapped[str] = mapped_column(String(500), default="gpt-4o-mini")
    system_prompt: Mapped[str] = mapped_column(
        OrEmptyText(), default="", nullable=True
    )  # 通用
    wecom_system_prompt: Mapped[str] = mapped_column(
        OrEmptyText(), default="", nullable=True
    )
    dingtalk_system_prompt: Mapped[str] = mapped_column(
        OrEmptyText(), default="", nullable=True
    )
    feishu_system_prompt: Mapped[str] = mapped_column(
        OrEmptyText(), default="", nullable=True
    )
    wecom_corp_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    wecom_secret: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    wecom_agent_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    wecom_redirect: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    dingtalk_app_key: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    dingtalk_app_secret: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    dingtalk_agent_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    dingtalk_redirect: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    feishu_app_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    feishu_app_secret: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    feishu_redirect: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    logo_path: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    favicon_path: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    site_title: Mapped[str] = mapped_column(String(500), default="askaibot")
    assistant_name: Mapped[str] = mapped_column(String(500), default="askaibot")
    assistant_avatar: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    admin_secret_enabled: Mapped[int] = mapped_column(Integer, default=0)
    admin_secret: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    theme: Mapped[str] = mapped_column(String(500), default="warm")
    debug_mode: Mapped[int] = mapped_column(Integer, default=1)
    sms_provider: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    sms_access_key_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    sms_secret: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    sms_sign_name: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    sms_template_code: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    sms_region: Mapped[str] = mapped_column(OrEmptyStr(500), default="", nullable=True)
    sms_sdk_app_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    sms_captcha_enabled: Mapped[int] = mapped_column(Integer, default=1)
    sms_captcha_provider: Mapped[str] = mapped_column(String(500), default="builtin")
    sms_cooldown: Mapped[int] = mapped_column(Integer, default=60)
    geetest_captcha_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    geetest_captcha_key: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    tencent_captcha_app_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    tencent_captcha_app_secret_key: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    aliyun_captcha_access_key_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    aliyun_captcha_access_key_secret: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    aliyun_captcha_scene_id: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    search_provider: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    search_api_key: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    search_base_url: Mapped[str] = mapped_column(
        OrEmptyStr(500), default="", nullable=True
    )
    search_auto: Mapped[int] = mapped_column(Integer, default=0)
    search_scope: Mapped[str] = mapped_column(
        String(255), default="global"
    )  # global / group
    token_limit_daily: Mapped[int | None] = mapped_column(Integer, nullable=True)
