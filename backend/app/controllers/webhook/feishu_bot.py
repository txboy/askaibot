import json
import logging
import sys
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import config
from app.services import feishu_bot as fs_core
from app.services import feishu_crypto as fc
from app import models
from app.database import get_db, get_sessionlocal
from app.services.wecom_bot import generate_reply


def SessionLocal():
    """动态获取当前会话工厂（热切换后仍指向新库）。"""
    return get_sessionlocal()()


logger = logging.getLogger("app.feishu_bot")
if config.debug:
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        _handler = logging.StreamHandler(sys.stderr)
        _handler.setLevel(logging.DEBUG)
        _handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(_handler)

router = APIRouter(prefix="/feishu/bot", tags=["feishu-bot"])


def _get_bot(db: Session, bot_id: int) -> models.WecomBot:
    bot = db.get(models.WecomBot, bot_id)
    if not bot or not bot.enabled or bot.provider != "feishu":
        logger.debug(
            f"[feishu-bot] bot unusable: id={bot_id} found={bot is not None} "
            f"enabled={bool(bot and bot.enabled)} "
            f"provider={(bot.provider if bot else None)!r}"
        )
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    bot = _get_bot(db, bot_id)
    raw = await request.body()
    logger.debug(f"[feishu-bot] callback received bot_id={bot_id} body_len={len(raw)}")
    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except Exception as exc:
        logger.debug(f"[feishu-bot] invalid JSON body_len={len(raw)} err={exc!r}")
        raise HTTPException(status_code=400, detail="无效的 JSON")

    inner_plain = None
    inner = body
    if "encrypt" in body:
        logger.debug(f"[feishu-bot] encrypted event aes_key_set={bool(bot.aes_key)}")
        if not bot.aes_key:
            logger.debug("[feishu-bot] encrypted event but aes_key empty -> 400")
            raise HTTPException(status_code=400, detail="未配置 Encrypt Key")
        try:
            inner_plain = fc.decrypt(bot.aes_key, body["encrypt"])
            inner = json.loads(inner_plain)
        except Exception as exc:
            logger.debug(f"[feishu-bot] decrypt FAILED err={exc!r}")
            raise HTTPException(
                status_code=403,
                detail=(
                    f"解密失败（请核对飞书事件订阅的 Encrypt Key 与本机器人的 EncryptKey 是否一致）：{exc}"
                ),
            )

    if inner.get("type") == "url_verification":
        challenge = inner.get("challenge", "")
        token_ok = (not bot.token) or inner.get("token") == bot.token
        logger.debug(
            f"[feishu-bot] url_verification challenge={challenge!r} token_ok={token_ok}"
        )
        if bot.token and inner.get("token") != bot.token:
            logger.debug("[feishu-bot] url_verification token mismatch -> 403")
            raise HTTPException(status_code=403, detail="校验 Token 不匹配")
        if "encrypt" in body:
            body_resp = {"encrypt": fc.encrypt(bot.aes_key, inner_plain or "")}
            logger.debug("[feishu-bot] url_verification encrypted response")
            return JSONResponse(body_resp)
        logger.debug("[feishu-bot] url_verification plaintext response")
        return JSONResponse({"challenge": challenge})

    # 消息事件：立即应答，避免飞书因超时重试导致重复回复，处理放到后台执行。
    event_id = (inner.get("header") or {}).get("event_id", "")
    logger.debug(f"[feishu-bot] event ack immediately event_id={event_id!r}")
    background_tasks.add_task(_process_event, bot_id, inner, event_id)
    return JSONResponse({"code": 0, "msg": "success"})


def _event_processed(db: Session, bot_id: int, event_id: str) -> bool:
    """标记事件已处理；若已存在（重试/重复推送）则返回 False。"""
    if not event_id:
        return True
    if db.query(models.BotEvent).filter(models.BotEvent.event_id == event_id).first():
        return False
    db.add(models.BotEvent(bot_id=bot_id, event_id=event_id))
    try:
        db.commit()
    except Exception:
        db.rollback()
        return False
    return True


async def _process_event(bot_id: int, inner: dict, event_id: str) -> None:
    db = SessionLocal()
    try:
        if not _event_processed(db, bot_id, event_id):
            logger.debug(f"[feishu-bot] duplicate event skipped event_id={event_id!r}")
            return
        bot = _get_bot(db, bot_id)
        logger.debug(
            f"[feishu-bot] process event event_id={event_id!r} bot_id={bot_id}"
        )
        await _handle(db, bot, inner)
    except Exception as exc:
        logger.debug(f"[feishu-bot] _process_event error err={exc!r}")
    finally:
        db.close()


async def _handle(db: Session, bot: models.WecomBot, body: dict) -> None:
    event = body.get("event") or {}
    message = event.get("message") or {}
    msg_type = message.get("message_type", "")

    sender = event.get("sender") or {}
    sid = sender.get("sender_id") or {}
    user_key = sid.get("open_id") or sid.get("union_id") or sender.get("id") or ""
    logger.debug(f"[feishu-bot] event msg_type={msg_type!r} user_key={user_key!r}")
    if not user_key:
        logger.debug("[feishu-bot] no sender id -> skip")
        return

    user = db.query(models.User).filter(models.User.feishu_userid == user_key).first()
    if not user:
        user = models.User(feishu_userid=user_key, nickname=f"飞书·{user_key[-6:]}")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.debug(f"[feishu-bot] created user id={user.id} userid={user_key}")
    else:
        logger.debug(f"[feishu-bot] found user id={user.id} userid={user_key}")

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
        logger.debug(
            f"[feishu-bot] created conversation id={conversation.id} bot_id={bot.id}"
        )
    else:
        logger.debug(
            f"[feishu-bot] found conversation id={conversation.id} bot_id={bot.id}"
        )

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
        logger.debug(f"[feishu-bot] non-text msg_type={msg_type!r} -> unsupported")
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
        logger.debug("[feishu-bot] empty text content -> skip")
        return

    db.add(
        models.Message(conversation_id=conversation.id, role="user", content=content)
    )
    db.flush()
    conversation.updated_at = datetime.now()
    db.commit()
    logger.debug(f"[feishu-bot] got text len={len(content)} content={content[:50]!r}")

    reply = await generate_reply(db, conversation, bot)
    logger.debug(
        f"[feishu-bot] reply len={len(reply or '')} preview={(reply or '')[:50]!r}"
    )
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

    try:
        await fs_core.send_text(
            user_key,
            reply or "抱歉，我暂时无法回答。",
            bot.corp_id,
            bot.secret,
        )
        logger.debug("[feishu-bot] send_text ok")
    except Exception as exc:
        logger.debug(f"[feishu-bot] send_text error err={exc!r}")
