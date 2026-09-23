"""企微智能机器人：access_token、主动发送、媒体下载与基于机器人配置的回复生成。"""

import time

import httpx
from sqlalchemy.orm import Session

from . import models
from .common import build_content_parts, get_setting, parse_models
from .kb import format_kb_context, retrieve_kb
from .search import format_results, search_web

_token_cache: dict[str, tuple[str, float]] = {}


async def get_access_token(corp_id: str, secret: str) -> str:
    cache_key = f"{corp_id}:{secret}"
    entry = _token_cache.get(cache_key)
    if entry and entry[1] > time.time():
        return entry[0]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={"corpid": corp_id, "corpsecret": secret},
        )
        data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(
            f"获取 access_token 失败：errcode={data.get('errcode')} errmsg={data.get('errmsg')}"
        )
    token = data["access_token"]
    expires = data.get("expires_in", 7200) - 300
    _token_cache[cache_key] = (token, time.time() + expires)
    return token


async def send_text(
    touser: str, content: str, agent_id: str, corp_id: str, secret: str
) -> None:
    token = await get_access_token(corp_id, secret)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={"access_token": token},
            json={
                "touser": touser,
                "msgtype": "text",
                "agentid": int(agent_id),
                "text": {"content": content},
            },
        )
        data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(
            f"发送消息失败：errcode={data.get('errcode')} errmsg={data.get('errmsg')}"
        )


async def download_media(media_id: str, corp_id: str, secret: str) -> bytes:
    token = await get_access_token(corp_id, secret)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/media/get",
            params={"access_token": token, "media_id": media_id},
        )
    return resp.content


def parse_kb_ids(kb_ids: str) -> list[int]:
    return [int(x) for x in kb_ids.split(",") if x.strip().isdigit()]


def _resolve_endpoint(db: Session, bot: models.WecomBot) -> models.ApiEndpoint:
    if bot.endpoint_id:
        ep = db.get(models.ApiEndpoint, bot.endpoint_id)
        if ep and ep.enabled:
            return ep
    ep = (
        db.query(models.ApiEndpoint)
        .filter(models.ApiEndpoint.enabled == 1)
        .order_by(models.ApiEndpoint.is_default.desc(), models.ApiEndpoint.id.asc())
        .first()
    )
    return ep


def _last_user_text(messages: list[models.Message]) -> str:
    for m in reversed(messages):
        if m.role == "user":
            return m.content
    return ""


async def build_context(db: Session, bot: models.WecomBot, query: str) -> str:
    parts: list[str] = []
    for kb_id in parse_kb_ids(bot.kb_ids):
        kb = db.get(models.KnowledgeBase, kb_id)
        if kb and kb.enabled:
            results = await retrieve_kb(kb.base_url, kb.api_key, query)
            ctx = format_kb_context(results)
            if ctx:
                parts.append(ctx)
    if bot.web_search:
        setting = get_setting(db)
        provider = setting.search_provider
        if provider:
            try:
                results = await search_web(
                    provider,
                    setting.search_api_key,
                    setting.search_base_url,
                    query,
                )
            except Exception:
                results = []
            txt = format_results(results)
            if txt:
                parts.append("请参考以下联网搜索结果：\n" + txt)
    return "\n\n".join(parts)


async def generate_reply(
    db: Session, conversation: models.Conversation, bot: models.WecomBot
) -> str:
    endpoint = _resolve_endpoint(db, bot)
    if not endpoint:
        raise RuntimeError("未配置可用接口，请联系管理员")
    base_url = endpoint.base_url.rstrip("/")
    api_key = endpoint.api_key
    models_list = parse_models(endpoint.models)
    model = bot.model or (models_list[0] if models_list else "")
    if not model:
        raise RuntimeError("未指定模型")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    history = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.id.asc())
        .all()
    )
    messages = []
    for m in history:
        atts = (
            db.query(models.Attachment)
            .filter(models.Attachment.message_id == m.id)
            .all()
        )
        if atts:
            messages.append(
                {"role": m.role, "content": build_content_parts(m.content, atts)}
            )
        else:
            messages.append({"role": m.role, "content": m.content})

    context = await build_context(db, bot, _last_user_text(history))
    if context:
        messages = [{"role": "system", "content": context}] + messages

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        data = resp.json()
    choice = (data.get("choices") or [{}])[0]
    return (choice.get("message") or {}).get("content", "").strip()
