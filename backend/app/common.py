import base64
import os

from sqlalchemy.orm import Session

from . import models
from .config import config


def get_setting(db: Session) -> models.Setting:
    setting = db.get(models.Setting, 1)
    if not setting:
        setting = models.Setting(id=1)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def resolve_system_prompt(
    db: Session,
    bot: models.WecomBot | None = None,
    endpoint: models.ApiEndpoint | None = None,
    provider: str | None = None,
) -> str:
    """按 机器人 > 基础配置(按平台) > 模型接口 > 通用 的优先级返回系统提示词。"""
    setting = get_setting(db)
    if bot and bot.system_prompt:
        return bot.system_prompt
    prov = provider or (bot.provider if bot else None)
    if prov == "wecom" and setting.wecom_system_prompt:
        return setting.wecom_system_prompt
    if prov == "dingtalk" and setting.dingtalk_system_prompt:
        return setting.dingtalk_system_prompt
    if prov == "feishu" and setting.feishu_system_prompt:
        return setting.feishu_system_prompt
    if endpoint and endpoint.system_prompt:
        return endpoint.system_prompt
    return setting.system_prompt or ""


def user_platform(user: models.User | None) -> str:
    """根据用户注册平台返回 provider（feishu/dingtalk/wecom），普通用户返回空串。"""
    if not user:
        return ""
    if user.feishu_userid:
        return "feishu"
    if user.dingtalk_userid:
        return "dingtalk"
    if user.wecom_userid:
        return "wecom"
    return ""


def mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return api_key[:4] + "****" + api_key[-4:]


def parse_models(models_str: str) -> list[str]:
    if not models_str:
        return []
    return [m.strip() for m in models_str.replace("\n", ",").split(",") if m.strip()]


def build_content_parts(text: str, attachments: list[models.Attachment]) -> list[dict]:
    parts: list[dict] = []
    if text:
        parts.append({"type": "text", "text": text})
    for att in attachments:
        if att.kind == "image":
            path = os.path.join(config.upload_dir, att.stored_name)
            if os.path.exists(path):
                data = open(path, "rb").read()
                b64 = base64.b64encode(data).decode()
                mime = att.content_type or "image/png"
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    }
                )
        else:
            parts.append(
                {
                    "type": "text",
                    "text": f"【附件：{att.filename}】\n{att.extracted_text or ''}",
                }
            )
    return parts
