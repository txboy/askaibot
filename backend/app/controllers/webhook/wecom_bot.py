import base64
import os
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

router = APIRouter(prefix="/wecom/bot", tags=["wecom-bot"])


def _get_bot(db: Session, bot_id: int) -> models.WecomBot:
    bot = db.get(models.WecomBot, bot_id)
    if not bot or not bot.enabled:
        raise HTTPException(status_code=404, detail="机器人不存在或未启用")
    return bot


def _receive_corp_id(bot: models.WecomBot, db: Session) -> str:
    if bot.corp_id:
        return bot.corp_id
    return get_setting(db).wecom_corp_id or bot.corp_id


def _extract_encrypt(body: bytes) -> str:
    root = ET.fromstring(body.decode("utf-8"))
    node = root.find("Encrypt")
    if node is None or not node.text:
        raise HTTPException(status_code=400, detail="缺少 Encrypt")
    return node.text


def _parse_message(xml: str) -> dict:
    root = ET.fromstring(xml)
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
    if wc.signature(bot.token, timestamp, nonce, echostr) != msg_signature:
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        plain = wc.decrypt_msg(
            base64.b64decode(echostr), bot.aes_key, _receive_corp_id(bot, db)
        )
    except Exception:
        raise HTTPException(status_code=403, detail="解密失败")
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
    body = await request.body()
    enc_str = _extract_encrypt(body)
    if wc.signature(bot.token, timestamp, nonce, enc_str) != msg_signature:
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        xml = wc.decrypt_msg(
            base64.b64decode(enc_str), bot.aes_key, _receive_corp_id(bot, db)
        )
    except Exception:
        raise HTTPException(status_code=403, detail="解密失败")

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
