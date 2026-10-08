"""企微智能机器人：access_token、主动发送、媒体下载与基于机器人配置的回复生成。"""

import json
import logging
import sys
import time

import httpx
from sqlalchemy.orm import Session

from app.config import config
from app.services import mcp as mcp_core
from app.services import skills as skill_core
from app import models
from app.common import (
    build_content_parts,
    get_setting,
    parse_models,
    resolve_system_prompt,
)
from app.services.kb import build_openai_tools, format_kb_context, retrieve_kb
from app.services.search import build_web_search_tool, format_results, search_web

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


def _bot_kbs(db: Session, bot: models.WecomBot) -> list[models.KnowledgeBase]:
    ids = parse_kb_ids(bot.kb_ids)
    if not ids:
        return []
    return (
        db.query(models.KnowledgeBase)
        .filter(
            models.KnowledgeBase.id.in_(ids),
            models.KnowledgeBase.enabled == 1,
        )
        .all()
    )


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

    # 机器人单独配置的 MCP 工具（默认由大模型选用）
    mcp_servers = mcp_core.resolve_servers(db, mcp_core.parse_ids(bot.mcp_ids))
    mcp_tools, mcp_mapping = await mcp_core.build_openai_tools(mcp_servers)

    # 机器人单独配置的技能
    skills = skill_core.resolve_skills_by_ids(db, skill_core.parse_ids(bot.skill_ids))
    skill_tools, skill_mapping = skill_core.build_openai_tools(skills)

    # 机器人绑定的知识库，以工具形式暴露给 LLM（默认使用，由大模型自主选择）
    bot_kbs = _bot_kbs(db, bot)
    kb_tools, kb_mapping = build_openai_tools(bot_kbs)

    # 联网搜索：作为可调用工具暴露给模型（机器人能力，不受用户 scope 限制）
    setting = get_setting(db)
    search_provider = setting.search_provider or ""
    web_search_enabled = bool(bot.web_search and search_provider)
    if web_search_enabled:
        logger.debug(
            f"[wecom-bot] web_search tool enabled provider={search_provider!r}"
        )

    base_tools: list[dict] = []
    if web_search_enabled:
        base_tools.append(build_web_search_tool())
    base_tools.extend(mcp_tools or [])
    base_tools.extend(skill_tools or [])
    base_tools.extend(kb_tools or [])
    tools = base_tools or None

    for s in skills:
        if s.content:
            messages = [{"role": "system", "content": s.content}] + messages

    # 系统提示词：按 机器人 > 基础配置 > 模型接口 > 通用 优先级取用，置于最前
    prompt = resolve_system_prompt(db, bot=bot, endpoint=endpoint)
    if prompt:
        logger.debug(f"[wecom-bot] system_prompt len={len(prompt)}")
        messages = [{"role": "system", "content": prompt}] + messages

    async with httpx.AsyncClient(timeout=120) as client:
        content = ""
        for round_index in range(3):
            body: dict = {"model": model, "messages": messages, "stream": False}
            if tools and round_index < 1:
                body["tools"] = tools
            logger.debug(
                f"[wecom-bot] LLM POST {base_url}/chat/completions round={round_index} "
                f"body={json.dumps(body, ensure_ascii=False)}"
            )
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.debug(
                f"[wecom-bot] LLM RESPONSE round={round_index} "
                f"data={json.dumps(data, ensure_ascii=False)}"
            )
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = (msg.get("content") or "").strip()
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return content
            if round_index >= 1:
                return content

            tool_messages = []
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name") or ""
                cid = tc.get("id") or "call_0"
                args: dict = {}
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {}
                if name == "web_search":
                    query = args.get("query", "")
                    logger.debug(
                        f"[wecom-bot] web_search provider={search_provider!r} query={query!r}"
                    )
                    try:
                        results = await search_web(
                            search_provider,
                            setting.search_api_key,
                            setting.search_base_url,
                            query,
                        )
                        tool_content = format_results(results)
                        logger.debug(
                            f"[wecom-bot] web_search_result results={len(results)}"
                        )
                    except Exception as exc:
                        logger.debug(f"[wecom-bot] web_search_error err={exc!r}")
                        tool_content = "联网搜索失败，请稍后重试。"
                elif name in mcp_mapping:
                    server, tool_name = mcp_mapping[name]
                    try:
                        tool_content = await mcp_core.call_tool(server, tool_name, args)
                    except Exception as exc:
                        tool_content = f"工具调用失败：{exc}"
                elif name in skill_mapping:
                    skill, tool = skill_mapping[name]
                    try:
                        tool_content = await skill_core.call_tool(skill, tool, args)
                    except Exception as exc:
                        tool_content = f"技能调用失败：{exc}"
                elif name in kb_mapping:
                    kb = kb_mapping[name]
                    try:
                        results = await retrieve_kb(
                            kb.provider,
                            kb.base_url,
                            kb.api_key,
                            kb.dataset_ids,
                            args.get("query", ""),
                            top_k=kb.top_k,
                        )
                        tool_content = (
                            format_kb_context(results) or "（未命中知识库内容）"
                        )
                    except Exception as exc:
                        tool_content = f"知识库检索失败：{exc}"
                else:
                    tool_content = "该工具不可用，请重试。"
                tool_messages.append(
                    {"role": "tool", "tool_call_id": cid, "content": tool_content}
                )
            messages = (
                messages
                + [{"role": "assistant", "content": None, "tool_calls": tool_calls}]
                + tool_messages
            )
    return content
