import json
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import mcp as mcp_core
from .. import skills as skill_core
from .. import models, schemas
from ..auth import get_current_user
from ..common import build_content_parts, get_setting, parse_models
from ..database import get_db
from ..kb import build_openai_tools, format_kb_context, retrieve_kb
from ..search import format_results, search_web

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
def chat(
    payload: schemas.ChatRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = db.get(models.Conversation, payload.conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    endpoint = None
    if payload.endpoint_id:
        endpoint = db.get(models.ApiEndpoint, payload.endpoint_id)
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

    base_url = endpoint.base_url.rstrip("/")
    api_key = endpoint.api_key
    models_list = parse_models(endpoint.models)
    model = payload.model or (models_list[0] if models_list else "")
    if not model:
        raise HTTPException(status_code=400, detail="未指定模型")

    attachments: list[models.Attachment] = []
    if payload.attachment_ids:
        attachments = (
            db.query(models.Attachment)
            .filter(
                models.Attachment.id.in_(payload.attachment_ids),
                models.Attachment.user_id == user.id,
            )
            .all()
        )
        for att in attachments:
            att.conversation_id = conversation.id
        db.commit()

    user_msg = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.content,
    )
    db.add(user_msg)
    db.flush()
    for att in attachments:
        att.message_id = user_msg.id
    conversation.updated_at = datetime.now()
    db.commit()
    db.refresh(user_msg)

    history = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.id.asc())
        .all()
    )

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

    kb_cfg = None
    if payload.knowledge_base_id:
        kb = db.get(models.KnowledgeBase, payload.knowledge_base_id)
        if kb and kb.enabled and kb.mode == "frontend":
            kb_cfg = kb

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    setting = get_setting(db)
    search_provider = setting.search_provider or ""
    should_search = (payload.web_search or bool(setting.search_auto)) and bool(
        search_provider
    )

    search_tool = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "联网搜索获取实时或最新信息，用于回答需要外部知识或最新数据的问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要搜索的关键词或完整问题",
                    }
                },
                "required": ["query"],
            },
        },
    }

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
                results = await retrieve_kb(
                    kb_cfg.provider,
                    kb_cfg.base_url,
                    kb_cfg.api_key,
                    kb_cfg.dataset_ids,
                    payload.content,
                    top_k=kb_cfg.top_k,
                )
                context = format_kb_context(results)
                if context:
                    current_messages = [
                        {"role": "system", "content": context}
                    ] + current_messages

            # 汇整 MCP 工具：默认（大模型选用）自动注入 + 会话前端选用的 MCP
            mcp_servers = list(mcp_core.all_servers(db, mode="llm"))
            selected_ids = mcp_core.parse_ids(conversation.mcp_ids)
            if selected_ids:
                mcp_servers.extend(
                    mcp_core.resolve_servers(db, selected_ids, mode="frontend")
                )
            mcp_tools, mcp_mapping = await mcp_core.build_openai_tools(mcp_servers)

            # 汇整技能：会话前端选用的技能（需用户可访问）
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
            if skill_system:
                current_messages = skill_system + current_messages
            skill_tools, skill_mapping = skill_core.build_openai_tools(skills)

            llm_kbs = (
                db.query(models.KnowledgeBase)
                .filter(
                    models.KnowledgeBase.enabled == 1,
                    models.KnowledgeBase.mode == "llm",
                )
                .all()
            )
            kb_tools, kb_mapping = build_openai_tools(llm_kbs)

            base_tools: list[dict] = []
            if should_search:
                base_tools.append(search_tool)
            base_tools.extend(mcp_tools)
            base_tools.extend(skill_tools)
            base_tools.extend(kb_tools)

            for round_index in range(3):
                body = {**request_body, "messages": current_messages}
                if base_tools:
                    body["tools"] = base_tools
                if round_index >= 1:
                    body.pop("tools", None)

                tool_calls_map = {}
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    ) as resp:
                        if resp.status_code != 200:
                            err = await resp.aread()
                            yield f"data: {json.dumps({'error': err.decode(errors='replace')})}\n\n"
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
                                usage_tokens = (
                                    obj["usage"].get("total_tokens") or usage_tokens
                                )
                                continue
                            choices = obj.get("choices") or []
                            if not choices:
                                continue
                            delta = choices[0].get("delta") or {}
                            delta_content = delta.get("content", "")
                            if delta_content:
                                full.append(delta_content)
                                yield f"data: {json.dumps({'delta': delta_content}, ensure_ascii=False)}\n\n"
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

                ready_calls = [
                    tool_calls_map[i]
                    for i in sorted(tool_calls_map)
                    if tool_calls_map[i]["name"]
                ]
                if not ready_calls:
                    break

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

                tool_messages: list[dict] = []
                for c in ready_calls:
                    name = c["name"]
                    cid = c["id"] or "call_0"
                    args: dict = {}
                    try:
                        args = json.loads(c["arguments"] or "{}")
                    except Exception:
                        args = {}
                    if name == "web_search":
                        yield f"data: {json.dumps({'status': 'searching'})}\n\n"
                        query = args.get("query", "")
                        try:
                            results = await search_web(
                                search_provider,
                                setting.search_api_key,
                                setting.search_base_url,
                                query,
                            )
                            content = format_results(results)
                        except Exception:
                            content = ""
                        tool_messages.append(
                            {"role": "tool", "tool_call_id": cid, "content": content}
                        )
                    elif name in mcp_mapping:
                        server, tool_name = mcp_mapping[name]
                        yield f"data: {json.dumps({'status': 'tool', 'server': server.name})}\n\n"
                        try:
                            content = await mcp_core.call_tool(server, tool_name, args)
                        except Exception as exc:
                            content = f"工具调用失败：{exc}"
                        tool_messages.append(
                            {"role": "tool", "tool_call_id": cid, "content": content}
                        )
                    elif name in skill_mapping:
                        skill, tool = skill_mapping[name]
                        yield f"data: {json.dumps({'status': 'tool', 'server': skill.name})}\n\n"
                        try:
                            content = await skill_core.call_tool(skill, tool, args)
                        except Exception as exc:
                            content = f"技能调用失败：{exc}"
                        tool_messages.append(
                            {"role": "tool", "tool_call_id": cid, "content": content}
                        )
                    elif name in kb_mapping:
                        kb = kb_mapping[name]
                        yield f"data: {json.dumps({'status': 'tool', 'server': kb.name})}\n\n"
                        try:
                            results = await retrieve_kb(
                                kb.provider,
                                kb.base_url,
                                kb.api_key,
                                kb.dataset_ids,
                                args.get("query", ""),
                                top_k=kb.top_k,
                            )
                            content = (
                                format_kb_context(results) or "（未命中知识库内容）"
                            )
                        except Exception as exc:
                            content = f"知识库检索失败：{exc}"
                        tool_messages.append(
                            {"role": "tool", "tool_call_id": cid, "content": content}
                        )
                    else:
                        tool_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": cid,
                                "content": "该工具不可用，请重试。",
                            }
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
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        assistant_text = "".join(full)
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
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
