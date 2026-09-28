import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.services import feishu_bot as fs_core
from app.services import feishu_crypto as fc
from app import models
from app.database import get_db
from app.services.wecom_bot import generate_reply

router = APIRouter(prefix="/feishu/bot", tags=["feishu-bot"])


def _get_bot(db: Session, bot_id: int) -> models.WecomBot:
    bot = db.get(models.WecomBot, bot_id)
    if not bot or not bot.enabled or bot.provider != "feishu":
        raise HTTPException(status_code=404, detail="机器人不存在或未启用")
    return bot


def _message_text(message: dict) -> str:
    msg_type = message.get("message_type", "")
    content = message.get("content", "")
    if msg_type != "text":
        return ""
    try:
        data = json.loads(content)
    except Exception:
        return content
    return data.get("text", "")


@router.post("/{bot_id}/callback")
async def receive(
    bot_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    bot = _get_bot(db, bot_id)
    raw = await request.body()
    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON")

    inner_plain = None
    inner = body
    if "encrypt" in body:
        if not bot.aes_key:
            raise HTTPException(status_code=400, detail="未配置 Encrypt Key")
        try:
            inner_plain = fc.decrypt(bot.aes_key, body["encrypt"])
            inner = json.loads(inner_plain)
        except Exception:
            raise HTTPException(status_code=403, detail="解密失败")

    if inner.get("type") == "url_verification":
        challenge = inner.get("challenge", "")
        if bot.token and inner.get("token") != bot.token:
            raise HTTPException(status_code=403, detail="校验 Token 不匹配")
        if "encrypt" in body:
            return JSONResponse({"encrypt": fc.encrypt(bot.aes_key, inner_plain or "")})
        return JSONResponse({"challenge": challenge})

    try:
        await _handle(db, bot, inner)
    except Exception:
        pass
    return JSONResponse({"code": 0, "msg": "success"})


async def _handle(db: Session, bot: models.WecomBot, body: dict) -> None:
    event = body.get("event") or {}
    message = event.get("message") or {}
    msg_type = message.get("message_type", "")

    sender = event.get("sender") or {}
    sid = sender.get("sender_id") or {}
    user_key = sid.get("open_id") or sid.get("union_id") or sender.get("id") or ""
    if not user_key:
        return

    user = db.query(models.User).filter(models.User.feishu_userid == user_key).first()
    if not user:
        user = models.User(feishu_userid=user_key, nickname=f"飞书·{user_key[-6:]}")
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
            user_id=user.id, bot_id=bot.id, title=f"飞书机器人·{bot.name}"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

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
        await fs_core.send_text(user_key, text, bot.corp_id, bot.secret)
        db.add(
            models.Message(
                conversation_id=conversation.id, role="assistant", content=text
            )
        )
        db.commit()
        return

    content = _message_text(message)
    if not content:
        return

    db.add(
        models.Message(conversation_id=conversation.id, role="user", content=content)
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

    await fs_core.send_text(
        user_key,
        reply or "抱歉，我暂时无法回答。",
        bot.corp_id,
        bot.secret,
    )
