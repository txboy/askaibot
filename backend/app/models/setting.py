from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    base_url: Mapped[str] = mapped_column(String, default="https://api.openai.com/v1")
    api_key: Mapped[str] = mapped_column(String, default="")
    default_model: Mapped[str] = mapped_column(String, default="gpt-4o-mini")
    system_prompt: Mapped[str] = mapped_column(Text, default="")  # 通用
    wecom_system_prompt: Mapped[str] = mapped_column(Text, default="")
    dingtalk_system_prompt: Mapped[str] = mapped_column(Text, default="")
    feishu_system_prompt: Mapped[str] = mapped_column(Text, default="")
    wecom_corp_id: Mapped[str] = mapped_column(String, default="")
    wecom_secret: Mapped[str] = mapped_column(String, default="")
    wecom_agent_id: Mapped[str] = mapped_column(String, default="")
    wecom_redirect: Mapped[str] = mapped_column(String, default="")
    dingtalk_app_key: Mapped[str] = mapped_column(String, default="")
    dingtalk_app_secret: Mapped[str] = mapped_column(String, default="")
    dingtalk_agent_id: Mapped[str] = mapped_column(String, default="")
    dingtalk_redirect: Mapped[str] = mapped_column(String, default="")
    feishu_app_id: Mapped[str] = mapped_column(String, default="")
    feishu_app_secret: Mapped[str] = mapped_column(String, default="")
    feishu_redirect: Mapped[str] = mapped_column(String, default="")
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
    sms_captcha_enabled: Mapped[int] = mapped_column(Integer, default=1)
    sms_captcha_provider: Mapped[str] = mapped_column(String, default="builtin")
    sms_cooldown: Mapped[int] = mapped_column(Integer, default=60)
    geetest_captcha_id: Mapped[str] = mapped_column(String, default="")
    geetest_captcha_key: Mapped[str] = mapped_column(String, default="")
    tencent_captcha_app_id: Mapped[str] = mapped_column(String, default="")
    tencent_captcha_app_secret_key: Mapped[str] = mapped_column(String, default="")
    aliyun_captcha_access_key_id: Mapped[str] = mapped_column(String, default="")
    aliyun_captcha_access_key_secret: Mapped[str] = mapped_column(String, default="")
    aliyun_captcha_scene_id: Mapped[str] = mapped_column(String, default="")
    search_provider: Mapped[str] = mapped_column(String, default="")
    search_api_key: Mapped[str] = mapped_column(String, default="")
    search_base_url: Mapped[str] = mapped_column(String, default="")
    search_auto: Mapped[int] = mapped_column(Integer, default=0)
    search_scope: Mapped[str] = mapped_column(
        String, default="global"
    )  # global / group
