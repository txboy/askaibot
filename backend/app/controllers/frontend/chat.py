import json
import logging
import sys
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import config
from app.services import mcp as mcp_core
from app.services import skills as skill_core
from app import models, schemas
from app.auth import get_current_user
from app.common import (
    build_content_parts,
    get_setting,
    parse_models,
    resolve_system_prompt,
    user_platform,
)
from app.database import get_db
from app.services.kb import build_openai_tools, format_kb_context, retrieve_kb
from app.services.search import format_results, search_web

logger = logging.getLogger("app.chat")
if config.debug:
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        _handler = logging.StreamHandler(sys.stderr)
        _handler.setLevel(logging.DEBUG)
        _handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(_handler)

router = APIRouter(prefix="/chat", tags=["chat"])


def _enforce_token_quota(db: Session, user: models.User) -> None:
    """若用户今日 token 已达有效每日限额，则硬性拦截（429）。"""
    from app.services import quota as quota_core

    limit = quota_core.effective_token_limit(db, user)
    if limit is None:
        return
    used = quota_core.used_tokens_today(db, user.id)
    if used >= limit:
        raise HTTPException(
            status_code=429, detail="今日 Token 限额已用完，请明日再试或联系管理员"
        )


@router.post("")
def chat(
    payload: schemas.ChatRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _enforce_token_quota(db, user)
    conversation = _get_owned_conversation(db, payload.conversation_id, user.id)
    endpoint = _resolve_endpoint(db, payload.endpoint_id, user)
    base_url = endpoint.base_url.rstrip("/")
    api_key = endpoint.api_key
    model = _resolve_model(payload, endpoint)
    logger.debug(
        f"[chat] user={user.id} conv={conversation.id} endpoint={endpoint.name} model={model} base_url={base_url}"
    )

    attachments = _attach_attachments(db, user, conversation, payload.attachment_ids)
    _save_user_message(db, conversation, payload.content, attachments)
    logger.debug(f"[chat] attachments={len(attachments)}")

    history = _load_history(db, conversation)
    openai_messages = _build_openai_messages(db, history)
    logger.debug(
        f"[chat] history={len(history)} openai_messages={len(openai_messages)}"
    )

    # 系统提示词：基础配置(用户注册平台) > 模型接口 > 通用，置于最前
    prompt = resolve_system_prompt(db, endpoint=endpoint, provider=user_platform(user))
    if prompt:
        logger.debug(f"[chat] system_prompt len={len(prompt)}")
        openai_messages = [{"role": "system", "content": prompt}] + openai_messages

    kb_cfg = _resolve_frontend_kb(db, payload.knowledge_base_id, user)
    headers = _build_request_headers(api_key)

    setting = get_setting(db)
    search_provider = setting.search_provider or ""
    should_search = _should_search(payload, setting, db, user)
    search_tool = _build_search_tool()
    logger.debug(
        f"[chat] kb={bool(kb_cfg)} web_search={should_search} search_provider={search_provider!r}"
    )

    request_body = {
        "model": model,
        "messages": openai_messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    async def generate():
        full = []
        usage_tokens = 0
        current_messages = openai_messages
        try:
            if kb_cfg:
                current_messages = await _inject_kb_context(
                    kb_cfg, current_messages, payload.content
                )
                logger.debug("[chat] kb_context=injected")

            (
                skill_system,
                base_tools,
                mcp_mapping,
                skill_mapping,
                kb_mapping,
            ) = await _build_tool_plan(
                db, conversation, user, should_search, search_tool
            )
            logger.debug(
                f"[chat] tools search={should_search} mcp={len(mcp_mapping)} skill={len(skill_mapping)} kb={len(kb_mapping)}"
            )
            if skill_system:
                current_messages = skill_system + current_messages

            for round_index in range(3):
                body = {**request_body, "messages": current_messages}
                if base_tools:
                    body["tools"] = base_tools
                if round_index >= 1:
                    body.pop("tools", None)
                logger.debug(
                    f"[chat] llm_request round={round_index + 1} body={json.dumps(body, ensure_ascii=False)}"
                )

                tool_calls_map = {}
                result = {}
                async with httpx.AsyncClient(timeout=None) as client:
                    stream = _stream_round(client, base_url, headers, body, result)
                    while True:
                        try:
                            chunk = await stream.__anext__()
                            yield f"data: {chunk}\n\n"
                        except StopAsyncIteration:
                            break
                if result["aborted"]:
                    logger.debug(f"[chat] round={round_index + 1} aborted")
                    return
                round_full = result["full"]
                round_usage = result["usage"]
                tool_calls_map = result["tool_calls_map"]
                full.extend(round_full)
                usage_tokens = round_usage or usage_tokens
                logger.debug(
                    f"[chat] round={round_index + 1} text_len={len(round_full)} usage={round_usage} tool_calls={len(tool_calls_map)}"
                )

                ready_calls = [
                    tool_calls_map[i]
                    for i in sorted(tool_calls_map)
                    if tool_calls_map[i]["name"]
                ]
                if not ready_calls:
                    break

                tool_calls_payload = _build_tool_calls_payload(ready_calls)

                tool_messages: list[dict] = []
                for c in ready_calls:
                    name = c["name"]
                    cid = c["id"] or "call_0"
                    args: dict = {}
                    try:
                        args = json.loads(c["arguments"] or "{}")
                    except Exception:
                        args = {}
                    logger.debug(
                        f"[chat] tool_call name={name} args={json.dumps(args, ensure_ascii=False)[:200]}"
                    )
                    status, content = await _run_tool_call(
                        name,
                        args,
                        search_provider,
                        setting,
                        mcp_mapping,
                        skill_mapping,
                        kb_mapping,
                    )
                    if status:
                        yield f"data: {json.dumps(status)}\n\n"
                    logger.debug(
                        f"[chat] tool_result name={name} content_len={len(content)}"
                    )
                    tool_messages.append(
                        {"role": "tool", "tool_call_id": cid, "content": content}
                    )

                current_messages = (
                    current_messages
                    + [
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls_payload,
                        }
                    ]
                    + tool_messages
                )
        except Exception as exc:
            logger.debug(f"[chat] error: {exc}")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        assistant_text = "".join(full)
        _save_assistant_message(
            db, conversation, endpoint, assistant_text, usage_tokens
        )
        logger.debug(f"[chat] done text_len={len(assistant_text)} usage={usage_tokens}")
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _get_owned_conversation(
    db: Session, conversation_id: int, user_id: int
) -> models.Conversation:
    """按会话 id 取回归属当前用户的会话，否则抛 404。"""
    conversation = db.get(models.Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conversation


def _resolve_endpoint(
    db: Session, endpoint_id: int | None, user: models.User
) -> models.ApiEndpoint:
    """解析本次聊天使用的 API 接口：优先用指定的，否则取默认启用的一个；需对当前用户可见。"""
    from app.services import groups as groups_core

    if endpoint_id:
        endpoint = db.get(models.ApiEndpoint, endpoint_id)
        if not endpoint or not endpoint.enabled:
            raise HTTPException(status_code=400, detail="所选接口不可用")
    else:
        endpoint = (
            db.query(models.ApiEndpoint)
            .filter(models.ApiEndpoint.enabled == 1)
            .order_by(models.ApiEndpoint.is_default.desc(), models.ApiEndpoint.id.asc())
            .first()
        )
    if not endpoint:
        raise HTTPException(status_code=400, detail="未配置可用接口，请联系管理员")
    if not groups_core.is_accessible(
        db, user.id, "endpoint", endpoint.id, endpoint.scope
    ):
        raise HTTPException(status_code=400, detail="所选接口不可用")
    return endpoint


def _resolve_model(payload: schemas.ChatRequest, endpoint: models.ApiEndpoint) -> str:
    """确定实际使用的模型名：优先取请求指定，否则用接口配置里的第一个。"""
    models_list = parse_models(endpoint.models)
    model = payload.model or (models_list[0] if models_list else "")
    if not model:
        raise HTTPException(status_code=400, detail="未指定模型")
    return model


def _attach_attachments(
    db: Session,
    user: models.User,
    conversation: models.Conversation,
    attachment_ids: list[int] | None,
) -> list[models.Attachment]:
    """按 id 取当前用户的附件并绑定到本会话，返回附件列表。"""
    attachments: list[models.Attachment] = []
    if attachment_ids:
        attachments = (
            db.query(models.Attachment)
            .filter(
                models.Attachment.id.in_(attachment_ids),
                models.Attachment.user_id == user.id,
            )
            .all()
        )
        for att in attachments:
            att.conversation_id = conversation.id
        db.commit()
    return attachments


def _save_user_message(
    db: Session,
    conversation: models.Conversation,
    content: str,
    attachments: list[models.Attachment],
) -> models.Message:
    """落库用户输入消息，并把附件挂到该消息上，返回消息对象。"""
    user_msg = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=content,
    )
    db.add(user_msg)
    db.flush()
    for att in attachments:
        att.message_id = user_msg.id
    conversation.updated_at = datetime.now()
    db.commit()
    db.refresh(user_msg)
    return user_msg


def _load_history(
    db: Session, conversation: models.Conversation
) -> list[models.Message]:
    """按时间顺序取回该会话的完整历史消息。"""
    return (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.id.asc())
        .all()
    )


def _build_openai_messages(db: Session, history: list[models.Message]) -> list[dict]:
    """把历史消息转成 OpenAI 聊天格式，带附件的消息拼成 content parts 数组。"""
    openai_messages = []
    for m in history:
        atts = (
            db.query(models.Attachment)
            .filter(models.Attachment.message_id == m.id)
            .all()
        )
        if atts:
            openai_messages.append(
                {"role": m.role, "content": build_content_parts(m.content, atts)}
            )
        else:
            openai_messages.append({"role": m.role, "content": m.content})
    return openai_messages


def _resolve_frontend_kb(
    db: Session, knowledge_base_id: int | None, user: models.User
) -> models.KnowledgeBase | None:
    """解析前端选用的知识库，仅接受对当前用户可见、启用且 mode 为 frontend 的配置，否则返回 None。"""
    if not knowledge_base_id:
        return None
    from app.services import groups as groups_core

    kb = db.get(models.KnowledgeBase, knowledge_base_id)
    if kb and kb.enabled and kb.mode == "frontend":
        if groups_core.is_accessible(db, user.id, "knowledge_base", kb.id, kb.scope):
            return kb
    return None


def _build_request_headers(api_key: str) -> dict:
    """构造请求头；有 API key 时附带 Bearer 鉴权。"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _should_search(
    payload: schemas.ChatRequest,
    setting: models.Setting,
    db: Session,
    user: models.User,
) -> bool:
    """判断本轮是否需要联网搜索（请求开启或系统默认开启，且已配置搜索服务，且用户被允许）。"""
    from app.services import groups as groups_core

    search_provider = setting.search_provider or ""
    if not search_provider:
        return False
    if not groups_core.can_search(db, user.id, setting):
        return False
    return payload.web_search or bool(setting.search_auto)


def _build_search_tool() -> dict:
    """构造 web_search 函数工具定义，用于让模型发起联网搜索。"""
    from app.services.search import build_web_search_tool

    return build_web_search_tool()


def _build_tool_calls_payload(ready_calls: list[dict]) -> list[dict]:
    """把已就绪的工具调用转成回填给模型的 assistant tool_calls 负载。"""
    tool_calls_payload = []
    for i, c in enumerate(ready_calls):
        tool_calls_payload.append(
            {
                "id": c["id"] or f"call_{i}",
                "type": "function",
                "function": {
                    "name": c["name"],
                    "arguments": c["arguments"] or "{}",
                },
            }
        )
    return tool_calls_payload


async def _inject_kb_context(
    kb_cfg: models.KnowledgeBase,
    messages: list[dict],
    user_content: str,
) -> list[dict]:
    """检索前端知识库并把命中上下文作为 system 消息注入到对话前部。"""
    logger.debug(
        f"[chat] kb_query provider={kb_cfg.provider} query={user_content!r} top_k={kb_cfg.top_k}"
    )
    results = await retrieve_kb(
        kb_cfg.provider,
        kb_cfg.base_url,
        kb_cfg.api_key,
        kb_cfg.dataset_ids,
        user_content,
        top_k=kb_cfg.top_k,
    )
    context = format_kb_context(results)
    logger.debug(
        f"[chat] kb_query_result hits={len(results)} context_len={len(context)}"
    )
    if context:
        return [{"role": "system", "content": context}] + messages
    return messages


async def _build_tool_plan(
    db: Session,
    conversation: models.Conversation,
    user: models.User,
    should_search: bool,
    search_tool: dict,
):
    """汇整可用工具（联网搜索 + MCP + 技能 + LLM 知识库），返回工具清单、各映射与技能 system 注入。"""
    from app.services import groups as groups_core

    mcp_servers = list(mcp_core.all_servers(db, mode="llm"))
    selected_ids = mcp_core.parse_ids(conversation.mcp_ids)
    if selected_ids:
        mcp_servers.extend(mcp_core.resolve_servers(db, selected_ids, mode="frontend"))
    mcp_servers = groups_core.filter_accessible(db, user.id, "mcp", mcp_servers)
    mcp_tools, mcp_mapping = await mcp_core.build_openai_tools(mcp_servers)

    selected_skill_ids = skill_core.parse_ids(conversation.skill_ids)
    if selected_skill_ids:
        accessible = {s.id for s in skill_core.user_skills(db, user.id)}
        skills = skill_core.resolve_skills_by_ids(
            db, [i for i in selected_skill_ids if i in accessible]
        )
    else:
        skills = []
    skill_system = [
        {"role": "system", "content": s.content} for s in skills if s.content
    ]
    skill_tools, skill_mapping = skill_core.build_openai_tools(skills)

    llm_kbs = (
        db.query(models.KnowledgeBase)
        .filter(
            models.KnowledgeBase.enabled == 1,
            models.KnowledgeBase.mode == "llm",
        )
        .all()
    )
    llm_kbs = groups_core.filter_accessible(db, user.id, "knowledge_base", llm_kbs)
    kb_tools, kb_mapping = build_openai_tools(llm_kbs)

    base_tools: list[dict] = []
    if should_search:
        base_tools.append(search_tool)
    base_tools.extend(mcp_tools)
    base_tools.extend(skill_tools)
    base_tools.extend(kb_tools)
    return skill_system, base_tools, mcp_mapping, skill_mapping, kb_mapping


async def _stream_round(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    body: dict,
    result: dict,
):
    """流式发送单轮请求并解析 SSE：yield 增量内容，结果写入 result（full/usage/tool_calls_map/aborted）。"""
    full: list[str] = []
    usage_tokens = 0
    tool_calls_map = {}
    async with client.stream(
        "POST",
        f"{base_url}/chat/completions",
        headers=headers,
        json=body,
    ) as resp:
        if resp.status_code != 200:
            err = await resp.aread()
            yield json.dumps({"error": err.decode(errors="replace")})
            result["full"] = []
            result["usage"] = 0
            result["tool_calls_map"] = {}
            result["aborted"] = True
            return
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except Exception:
                continue
            if obj.get("usage"):
                usage_tokens = obj["usage"].get("total_tokens") or usage_tokens
                continue
            choices = obj.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            delta_content = delta.get("content", "")
            if delta_content:
                full.append(delta_content)
                yield json.dumps({"delta": delta_content}, ensure_ascii=False)
            for tc in delta.get("tool_calls") or []:
                idx = tc.get("index", 0)
                entry = tool_calls_map.setdefault(
                    idx, {"id": "", "name": "", "arguments": ""}
                )
                if tc.get("id"):
                    entry["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    entry["name"] = fn["name"]
                if fn.get("arguments"):
                    entry["arguments"] += fn["arguments"]
    result["full"] = full
    result["usage"] = usage_tokens
    result["tool_calls_map"] = tool_calls_map
    result["aborted"] = False


async def _run_tool_call(
    name: str,
    args: dict,
    search_provider: str,
    setting: models.Setting,
    mcp_mapping: dict,
    skill_mapping: dict,
    kb_mapping: dict,
):
    """执行单个工具调用，返回 (状态事件, 结果内容)；未知工具返回不可用提示。"""
    if name == "web_search":
        status = {"status": "searching"}
        query = args.get("query", "")
        logger.debug(f"[chat] web_search provider={search_provider!r} query={query!r}")
        try:
            results = await search_web(
                search_provider,
                setting.search_api_key,
                setting.search_base_url,
                query,
            )
            content = format_results(results)
            logger.debug(
                f"[chat] web_search_result results={len(results)} content_len={len(content)}"
            )
        except Exception as exc:
            logger.debug(f"[chat] web_search_error err={exc}")
            content = ""
        return status, content
    if name in mcp_mapping:
        server, tool_name = mcp_mapping[name]
        status = {"status": "tool", "server": server.name}
        logger.debug(
            f"[chat] mcp_call server={server.name} tool={tool_name} args={json.dumps(args, ensure_ascii=False)}"
        )
        try:
            content = await mcp_core.call_tool(server, tool_name, args)
            logger.debug(
                f"[chat] mcp_result server={server.name} tool={tool_name} content_len={len(content)}"
            )
        except Exception as exc:
            logger.debug(
                f"[chat] mcp_error server={server.name} tool={tool_name} err={exc}"
            )
            content = f"工具调用失败：{exc}"
        return status, content
    if name in skill_mapping:
        skill, tool = skill_mapping[name]
        status = {"status": "tool", "server": skill.name}
        logger.debug(
            f"[chat] skill_call name={skill.name} tool={tool} args={json.dumps(args, ensure_ascii=False)}"
        )
        try:
            content = await skill_core.call_tool(skill, tool, args)
            logger.debug(
                f"[chat] skill_result name={skill.name} tool={tool} content_len={len(content)}"
            )
        except Exception as exc:
            logger.debug(f"[chat] skill_error name={skill.name} tool={tool} err={exc}")
            content = f"技能调用失败：{exc}"
        return status, content
    if name in kb_mapping:
        kb = kb_mapping[name]
        status = {"status": "tool", "server": kb.name}
        logger.debug(
            f"[chat] kb_call name={kb.name} provider={kb.provider} query={args.get('query', '')!r}"
        )
        try:
            results = await retrieve_kb(
                kb.provider,
                kb.base_url,
                kb.api_key,
                kb.dataset_ids,
                args.get("query", ""),
                top_k=kb.top_k,
            )
            content = format_kb_context(results) or "（未命中知识库内容）"
            logger.debug(
                f"[chat] kb_result name={kb.name} hits={len(results)} content_len={len(content)}"
            )
        except Exception as exc:
            logger.debug(f"[chat] kb_error name={kb.name} err={exc}")
            content = f"知识库检索失败：{exc}"
        return status, content
    return None, "该工具不可用，请重试。"


def _save_assistant_message(
    db: Session,
    conversation: models.Conversation,
    endpoint: models.ApiEndpoint,
    assistant_text: str,
    usage_tokens: int,
) -> None:
    """把生成的助手回复落库（含 token 与接口归属），并刷新会话更新时间。"""
    if assistant_text:
        db.add(
            models.Message(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_text,
                tokens=usage_tokens,
                endpoint_id=endpoint.id,
            )
        )
        conversation.updated_at = datetime.now()
        db.commit()
