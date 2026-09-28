"""外部知识库检索：仅对接 Dify / RAGFlow 的检索 API。

使用模式：
- frontend：前台聊天界面提供选择器，用户选中后直接注入检索上下文；
- llm：作为 function calling 工具暴露，由大模型自主决定是否检索、检索哪个库。
"""

import httpx

PROVIDERS = {"dify", "ragflow"}
PREFIX = "kb__"


def _slug(name: str) -> str:
    out = []
    for ch in name or "":
        out.append(ch if (ch.isascii() and (ch.isalnum() or ch == "-")) else "_")
    return "".join(out).strip("_") or "kb"


def _parse_dify(data: dict) -> list[dict]:
    records = data.get("records") or []
    out: list[dict] = []
    for r in records:
        seg = r.get("segment") or {}
        content = (seg.get("content") or "").strip()
        doc = seg.get("document") or {}
        source = doc.get("name") or ""
        if content:
            out.append(
                {"title": source or "片段", "content": content, "source": source}
            )
    return out


def _parse_ragflow(data: dict) -> list[dict]:
    if data.get("code") not in (0,):
        return []
    chunks = (data.get("data") or {}).get("chunks") or []
    out: list[dict] = []
    for c in chunks:
        content = (c.get("content") or "").strip()
        source = c.get("document_name") or c.get("document_keyword") or ""
        if content:
            out.append(
                {"title": source or "片段", "content": content, "source": source}
            )
    return out


def _dataset_list(dataset_ids: str) -> list[str]:
    return [x.strip() for x in (dataset_ids or "").split(",") if x.strip()]


async def retrieve_kb(
    provider: str,
    base_url: str,
    api_key: str,
    dataset_ids: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    provider = (provider or "dify").lower()
    if provider not in PROVIDERS or not base_url:
        return []
    ids = _dataset_list(dataset_ids)
    if not ids:
        return []
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if provider == "dify":
                url = f"{base_url.rstrip('/')}/datasets/{ids[0]}/retrieve"
                body = {
                    "query": query,
                    "retrieval_model": {
                        "search_method": "hybrid_search",
                        "top_k": top_k,
                        "score_threshold_enabled": False,
                        "reranking_enable": False,
                    },
                }
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                return _parse_dify(resp.json())
            else:
                url = f"{base_url.rstrip('/')}/api/v1/retrieval"
                body = {"question": query, "dataset_ids": ids, "page_size": top_k}
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                return _parse_ragflow(resp.json())
    except Exception:
        return []


def build_openai_tools(kbs: list) -> tuple[list[dict], dict[str, object]]:
    """把 llm 模式知识库暴露为 function calling 工具；名称按知识库命名空间化。"""
    tools: list[dict] = []
    mapping: dict[str, object] = {}
    seen: set[str] = set()
    for kb in kbs:
        slug = _slug(kb.name)
        name = f"{PREFIX}{slug}__{kb.id}__retrieve"
        if name in seen:
            continue
        seen.add(name)
        mapping[name] = kb
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": f"检索知识库「{kb.name}」的内容。当需要基于该知识库的信息回答用户问题时可调用该工具。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "检索关键词或完整问题",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
        )
    return tools, mapping


def format_kb_context(results: list[dict]) -> str:
    if not results:
        return ""
    lines = []
    for i, r in enumerate(results, 1):
        text = (r.get("content") or "").strip()
        if len(text) > 1000:
            text = text[:1000] + "…"
        source = r.get("source") or ""
        head = f"{i}. {r.get('title') or '片段'}"
        if source:
            head += f"（来源：{source}）"
        lines.append(f"{head}\n{text}")
    return "请基于以下知识库内容回答用户的问题：\n\n" + "\n\n".join(lines)
