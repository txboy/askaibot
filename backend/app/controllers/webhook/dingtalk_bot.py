import base64
import json
import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.services import dingtalk_bot as dt_core
from app import models
from app.config import config
from app.services import wecom_crypto as wc
from app.database import get_db
from app.services.wecom_bot import generate_reply

logger = logging.getLogger("app.dingtalk_bot")
if config.debug:
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        _handler = logging.StreamHandler(sys.stderr)
        _handler.setLevel(logging.DEBUG)
        _handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(_handler)

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


def _parse_message(content: str) -> dict:
    """解析钉钉回调明文：兼容 XML 与 JSON 两种消息格式。"""
    text = (content or "").strip()
    if not text:
        raise ValueError("空消息体")
    # XML 格式（与企微一致）
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
    # JSON 格式（钉钉机器人消息回调）
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON 消息必须是对象")
    text_obj = data.get("text")
    content = ""
    if isinstance(text_obj, dict):
        content = text_obj.get("content", "")
    else:
        content = data.get("content") or data.get("Content") or ""
    return {
        "ToUserName": (
            data.get("toUserId") or data.get("robotCode") or data.get("corpId") or ""
        ),
        "FromUserName": (
            data.get("senderStaffId")
            or data.get("senderId")
            or data.get("senderUserId")
            or data.get("fromUserId")
            or data.get("senderNick")
            or ""
        ),
        "MsgType": data.get("msgtype") or data.get("msgType") or "",
        "Content": content,
        "MediaId": data.get("mediaId") or data.get("MediaId") or "",
        "PicUrl": data.get("picUrl") or data.get("PicUrl") or "",
    }


def _is_check_url(content: str) -> bool:
    """判断是否为钉钉的 URL 校验事件 check_url。"""
    try:
        data = json.loads((content or "").strip())
    except Exception:
        return False
    return isinstance(data, dict) and data.get("EventType") == "check_url"


def _check_url_response(
    bot: models.WecomBot, timestamp: str, nonce: str, receive_id: str
) -> Response:
    """钉钉 URL 校验要求返回 JSON：encrypt 解密后须为明文 "success"。

    响应字段：msg_signature / timeStamp / nonce / encrypt。
    """
    plain = "success"
    enc = base64.b64encode(wc.encrypt_msg(plain, bot.aes_key, receive_id)).decode(
        "utf-8"
    )
    msg_sig = wc.signature(bot.token, timestamp, nonce, enc)
    payload = {
        "msg_signature": msg_sig,
        "timeStamp": timestamp,
        "nonce": nonce,
        "encrypt": enc,
    }
    return Response(content=json.dumps(payload), media_type="application/json")


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
    # 钉钉「调试」按钮发起的裸 GET 连通性检查（无任何查询参数）
    if not sig and not echostr:
        logger.info("[dingtalk-bot] 钉钉调试空 GET 连通性检查，返回 success")
        return Response(content="success", media_type="text/plain")
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
    logger.info(
        "[dingtalk-bot] 收到回调 bot=%s ts=%s nonce=%s enc_len=%s",
        bot_id,
        timestamp,
        nonce,
        len(enc),
    )
    if not _valid_signature(bot, timestamp, nonce, enc, sig):
        logger.error("[dingtalk-bot] 签名验证失败")
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        xml, rid = wc.decrypt_msg_with_rid(
            base64.b64decode(enc), bot.aes_key, check_receive_id=False
        )
    except Exception as exc:
        logger.error("[dingtalk-bot] 解密失败: %r", exc)
        raise HTTPException(status_code=403, detail="解密失败")
    logger.info("[dingtalk-bot] 解密明文=%r", (xml or "")[:2000])

    # 钉钉 URL 校验事件：返回加密的 "success" JSON（msg_signature/timeStamp/nonce/encrypt）
    if _is_check_url(xml):
        logger.info(
            "[dingtalk-bot] check_url 校验，返回加密 success 响应 receive_id=%r",
            rid,
        )
        return _check_url_response(bot, timestamp, nonce, rid)

    try:
        msg = _parse_message(xml)
    except Exception as exc:
        # 无法解析为消息时，返回 success 确认
        logger.info(
            "[dingtalk-bot] 非消息回调 xml=%r err=%r，返回 success",
            (xml or "")[:2000],
            exc,
        )
        return Response(content="success", media_type="text/plain")

    # 解析成功但缺少发送者/消息类型，视为非消息事件，返回 success
    if not msg.get("FromUserName") or not msg.get("MsgType"):
        logger.info(
            "[dingtalk-bot] 非真实消息(缺 FromUserName/MsgType) msg=%r，返回 success",
            msg,
        )
        return Response(content="success", media_type="text/plain")

    try:
        await _handle(db, bot, msg)
    except Exception:
        logger.exception("[dingtalk-bot] 处理消息出错")
        # 记录并返回 200，避免钉钉反复重试
    return Response(content="success", media_type="text/plain")


async def _handle(db: Session, bot: models.WecomBot, msg: dict) -> None:
    from_user = msg.get("FromUserName", "")
    if not from_user:
        return

    user = (
        db.query(models.User).filter(models.User.dingtalk_userid == from_user).first()
    )
    if not user:
        user = models.User(dingtalk_userid=from_user, nickname=f"钉钉·{from_user[-6:]}")
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
        await dt_core.send_text(from_user, text, bot.agent_id, bot.corp_id, bot.secret)
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
