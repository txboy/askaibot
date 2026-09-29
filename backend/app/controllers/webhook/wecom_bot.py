import base64
import json
import logging
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import models
from app.services import wecom_crypto as wc, wecom_bot as bot_core
from app.common import get_setting
from app.config import config
from app.database import get_db

logger = logging.getLogger("app.wecom_bot")
if config.debug:
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        _handler = logging.StreamHandler(sys.stderr)
        _handler.setLevel(logging.DEBUG)
        _handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(_handler)

router = APIRouter(prefix="/wecom/bot", tags=["wecom-bot"])


def _get_bot(db: Session, bot_id: int) -> models.WecomBot:
    bot = db.get(models.WecomBot, bot_id)
    if not bot or not bot.enabled:
        raise HTTPException(status_code=404, detail="机器人不存在或未启用")
    return bot


def _log_bot_config(bot: models.WecomBot, db: Session) -> None:
    """以 debug 级别输出机器人配置信息（密钥类仅输出是否已设置）。"""
    setting = get_setting(db)
    logger.debug(
        "[wecom-bot] 机器人配置 bot=%s name=%r provider=%r enabled=%s "
        "corp_id=%r agent_id=%r token_set=%s aes_key_set=%s secret_set=%s "
        "fallback_wecom_corp_id=%r",
        bot.id,
        bot.name,
        bot.provider,
        bot.enabled,
        bot.corp_id,
        bot.agent_id,
        bool(bot.token),
        bool(bot.aes_key),
        bool(bot.secret),
        setting.wecom_corp_id,
    )


def _receive_corp_id(bot: models.WecomBot, db: Session) -> str:
    if bot.corp_id:
        return bot.corp_id
    return get_setting(db).wecom_corp_id or bot.corp_id


def _extract_encrypt(body: bytes) -> str:
    text = body.decode("utf-8")
    # JSON 格式（部分企微回调以 JSON 发送 encrypt 字段）
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except Exception:
            data = None
        if isinstance(data, dict) and data.get("encrypt"):
            return data["encrypt"]
    # XML 格式（与企微文档一致）
    root = ET.fromstring(text)
    node = root.find("Encrypt")
    if node is None or not node.text:
        raise HTTPException(status_code=400, detail="缺少 Encrypt")
    return node.text


def _parse_message(content: str) -> dict:
    """解析企微回调明文：兼容 XML 与 JSON（企微 AI 机器人）两种格式。"""
    text = (content or "").strip()
    if not text:
        raise ValueError("空消息体")
    if text.startswith("<"):
        root = ET.fromstring(text)
        msg = {}
        for tag in (
            "ToUserName",
            "FromUserName",
            "MsgType",
            "Content",
            "MediaId",
            "PicUrl",
        ):
            node = root.find(tag)
            msg[tag] = (node.text or "") if node is not None else ""
        return msg
    # JSON 格式（企微 AI 机器人，如 {"chattype":"single","from":{"userid":...},"msgtype":"text","text":{"content":...}}）
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON 消息必须是对象")
    from_obj = data.get("from")
    if isinstance(from_obj, dict):
        from_user = (
            from_obj.get("userid")
            or from_obj.get("open_userid")
            or from_obj.get("user_id")
            or ""
        )
    else:
        from_user = data.get("from") or ""
    text_obj = data.get("text")
    if isinstance(text_obj, dict):
        content = text_obj.get("content", "")
    else:
        content = data.get("content") or data.get("Content") or ""
    return {
        "ToUserName": data.get("aibotid") or data.get("corpId") or "",
        "FromUserName": from_user,
        "MsgType": data.get("msgtype") or data.get("msgType") or "",
        "Content": content,
        "MediaId": data.get("media_id") or data.get("MediaId") or "",
        "PicUrl": data.get("pic_url") or data.get("PicUrl") or "",
    }


def _guess_image(media_id: str, data: bytes) -> tuple[str, str]:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"
    if data[:3] == b"GIF":
        return "image/gif", ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return "image/jpeg", ".jpg"


@router.get("/{bot_id}/callback")
def verify(
    bot_id: int,
    msg_signature: str,
    timestamp: str,
    nonce: str,
    echostr: str,
    db: Session = Depends(get_db),
):
    bot = _get_bot(db, bot_id)
    _log_bot_config(bot, db)
    logger.info(
        "[wecom-bot] 收到 URL 校验 bot=%s ts=%s nonce=%s",
        bot_id,
        timestamp,
        nonce,
    )
    calc = wc.signature(bot.token, timestamp, nonce, echostr)
    if calc != msg_signature:
        logger.error(
            "[wecom-bot] 签名验证失败 bot=%s 期望=%s 计算=%s token_set=%s",
            bot_id,
            msg_signature,
            calc,
            bool(bot.token),
        )
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        rid = _receive_corp_id(bot, db)
        plain, embedded_rid = wc.decrypt_msg_with_rid(
            base64.b64decode(echostr), bot.aes_key, check_receive_id=False
        )
        logger.debug(
            "[wecom-bot] URL 校验解密成功 bot=%s receive_id(配置)=%r 内嵌=%r",
            bot_id,
            rid,
            embedded_rid,
        )
    except Exception as exc:
        logger.error(
            "[wecom-bot] 解密失败 bot=%s corp_id=%r aes_key_set=%s err=%r",
            bot_id,
            _receive_corp_id(bot, db),
            bool(bot.aes_key),
            exc,
        )
        raise HTTPException(status_code=403, detail="解密失败")
    logger.info("[wecom-bot] URL 校验成功，回显明文=%r", (plain or "")[:200])
    return Response(content=plain, media_type="text/plain")


@router.post("/{bot_id}/callback")
async def receive(
    bot_id: int,
    request: Request,
    msg_signature: str,
    timestamp: str,
    nonce: str,
    db: Session = Depends(get_db),
):
    bot = _get_bot(db, bot_id)
    _log_bot_config(bot, db)
    body = await request.body()
    enc_str = _extract_encrypt(body)
    logger.info(
        "[wecom-bot] 收到回调 bot=%s ts=%s nonce=%s enc_len=%s",
        bot_id,
        timestamp,
        nonce,
        len(enc_str),
    )
    calc = wc.signature(bot.token, timestamp, nonce, enc_str)
    if calc != msg_signature:
        logger.error(
            "[wecom-bot] 签名验证失败 bot=%s 期望=%s 计算=%s token_set=%s",
            bot_id,
            msg_signature,
            calc,
            bool(bot.token),
        )
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        rid = _receive_corp_id(bot, db)
        xml, embedded_rid = wc.decrypt_msg_with_rid(
            base64.b64decode(enc_str), bot.aes_key, check_receive_id=False
        )
        logger.debug(
            "[wecom-bot] 解密回调成功 bot=%s receive_id(配置)=%r 内嵌=%r",
            bot_id,
            rid,
            embedded_rid,
        )
    except Exception as exc:
        logger.error(
            "[wecom-bot] 解密失败 bot=%s corp_id=%r aes_key_set=%s err=%r",
            bot_id,
            _receive_corp_id(bot, db),
            bool(bot.aes_key),
            exc,
        )
        raise HTTPException(status_code=403, detail="解密失败")
    logger.info("[wecom-bot] 解密明文=%r", (xml or "")[:2000])

    msg = _parse_message(xml)
    try:
        await _handle(db, bot, msg)
    except Exception:
        # 记录并返回 200，避免企微反复重试
        pass
    return Response(content="success", media_type="text/plain")


async def _handle(db: Session, bot: models.WecomBot, msg: dict) -> None:
    from_user = msg.get("FromUserName", "")
    if not from_user:
        return

    user = db.query(models.User).filter(models.User.wecom_userid == from_user).first()
    if not user:
        user = models.User(wecom_userid=from_user, nickname=f"企微·{from_user[-6:]}")
        db.add(user)
        db.commit()
        db.refresh(user)

    conversation = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.user_id == user.id,
            models.Conversation.bot_id == bot.id,
        )
        .first()
    )
    if not conversation:
        conversation = models.Conversation(
            user_id=user.id, bot_id=bot.id, title=f"企微机器人·{bot.name}"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    msg_type = msg.get("MsgType", "")
    if msg_type == "text":
        content = msg.get("Content", "")
        user_msg = models.Message(
            conversation_id=conversation.id, role="user", content=content
        )
        db.add(user_msg)
        db.flush()
    elif msg_type == "image":
        media_id = msg.get("MediaId", "")
        data = await bot_core.download_media(
            media_id, _receive_corp_id(bot, db), bot.secret
        )
        user_msg = models.Message(
            conversation_id=conversation.id, role="user", content=""
        )
        db.add(user_msg)
        db.flush()
        stored = f"{uuid.uuid4().hex}{_guess_image(media_id, data)[1]}"
        os.makedirs(config.upload_dir, exist_ok=True)
        with open(os.path.join(config.upload_dir, stored), "wb") as f:
            f.write(data)
        mime, _ = _guess_image(media_id, data)
        att = models.Attachment(
            user_id=user.id,
            conversation_id=conversation.id,
            message_id=user_msg.id,
            filename=f"wecom_{stored}",
            stored_name=stored,
            content_type=mime,
            kind="image",
            size=len(data),
        )
        db.add(att)
    elif msg_type in ("voice", "video", "file", "event", "location"):
        text = "暂不支持该类型消息，请发送文字或图片。"
        user_msg = models.Message(
            conversation_id=conversation.id, role="user", content=f"[{msg_type}消息]"
        )
        db.add(user_msg)
        db.flush()
        await bot_core.send_text(
            from_user, text, bot.agent_id, _receive_corp_id(bot, db), bot.secret
        )
        db.add(
            models.Message(
                conversation_id=conversation.id, role="assistant", content=text
            )
        )
        db.commit()
        return
    else:
        return

    conversation.updated_at = datetime.now()
    db.commit()

    reply = await bot_core.generate_reply(db, conversation, bot)
    if reply:
        db.add(
            models.Message(
                conversation_id=conversation.id,
                role="assistant",
                content=reply,
                endpoint_id=bot.endpoint_id,
            )
        )
        db.commit()

    await bot_core.send_text(
        from_user,
        reply or "抱歉，我暂时无法回答。",
        bot.agent_id,
        _receive_corp_id(bot, db),
        bot.secret,
    )
