import base64
import json
import xml.etree.ElementTree as ET
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import dingtalk_bot as dt_core
from .. import models, wecom_crypto as wc
from ..database import get_db
from ..wecom_bot import generate_reply

router = APIRouter(prefix="/dingtalk/bot", tags=["dingtalk-bot"])


def _get_bot(db: Session, bot_id: int) -> models.WecomBot:
    bot = db.get(models.WecomBot, bot_id)
    if not bot or not bot.enabled or bot.provider != "dingtalk":
        raise HTTPException(status_code=404, detail="机器人不存在或未启用")
    return bot


def _extract_encrypt(body: bytes) -> str:
    text = body.decode("utf-8")
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("encrypt"):
            return data["encrypt"]
    except Exception:
        pass
    root = ET.fromstring(text)
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


def _valid_signature(
    bot: models.WecomBot, timestamp: str, nonce: str, encrypt: str, given: str
) -> bool:
    return wc.signature(bot.token, timestamp, nonce, encrypt) == given


@router.get("/{bot_id}/callback")
def verify(
    bot_id: int,
    signature: str = Query(""),
    msg_signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
    echostr: str = Query(""),
    db: Session = Depends(get_db),
):
    bot = _get_bot(db, bot_id)
    sig = signature or msg_signature
    if not _valid_signature(bot, timestamp, nonce, echostr, sig):
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        plain = wc.decrypt_msg(
            base64.b64decode(echostr), bot.aes_key, "", check_receive_id=False
        )
    except Exception:
        raise HTTPException(status_code=403, detail="解密失败")
    return Response(content=plain, media_type="text/plain")


@router.post("/{bot_id}/callback")
async def receive(
    bot_id: int,
    request: Request,
    signature: str = Query(""),
    msg_signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
    db: Session = Depends(get_db),
):
    bot = _get_bot(db, bot_id)
    body = await request.body()
    enc = _extract_encrypt(body)
    sig = signature or msg_signature
    if not _valid_signature(bot, timestamp, nonce, enc, sig):
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        xml = wc.decrypt_msg(
            base64.b64decode(enc), bot.aes_key, "", check_receive_id=False
        )
    except Exception:
        raise HTTPException(status_code=403, detail="解密失败")

    msg = _parse_message(xml)
    try:
        await _handle(db, bot, msg)
    except Exception:
        # 记录并返回 200，避免钉钉反复重试
        pass
    return Response(content="success", media_type="text/plain")


async def _handle(db: Session, bot: models.WecomBot, msg: dict) -> None:
    from_user = msg.get("FromUserName", "")
    if not from_user:
        return

    user = (
        db.query(models.User)
        .filter(models.User.dingtalk_userid == from_user)
        .first()
    )
    if not user:
        user = models.User(
            dingtalk_userid=from_user, nickname=f"钉钉·{from_user[-6:]}"
        )
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
            user_id=user.id, bot_id=bot.id, title=f"钉钉机器人·{bot.name}"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    msg_type = msg.get("MsgType", "")
    if msg_type != "text":
        text = "暂不支持该类型消息，请发送文字。"
        db.add(
            models.Message(
                conversation_id=conversation.id,
                role="user",
                content=f"[{msg_type}消息]",
            )
        )
        db.flush()
        await dt_core.send_text(
            from_user, text, bot.agent_id, bot.corp_id, bot.secret
        )
        db.add(
            models.Message(
                conversation_id=conversation.id, role="assistant", content=text
            )
        )
        db.commit()
        return

    db.add(
        models.Message(
            conversation_id=conversation.id,
            role="user",
            content=msg.get("Content", ""),
        )
    )
    db.flush()
    conversation.updated_at = datetime.now()
    db.commit()

    reply = await generate_reply(db, conversation, bot)
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

    await dt_core.send_text(
        from_user,
        reply or "抱歉，我暂时无法回答。",
        bot.agent_id,
        bot.corp_id,
        bot.secret,
    )
