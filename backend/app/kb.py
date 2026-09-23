"""外部知识库检索：按固定契约调用后台配置的通用检索 HTTP API。"""

import httpx


async def retrieve_kb(
    base_url: str,
    api_key: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    if not base_url:
        return []
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                base_url,
                json={"query": query, "top_k": top_k},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    results = data.get("results") or []
    return [
        {
            "title": r.get("title", ""),
            "content": r.get("content", ""),
            "source": r.get("source", ""),
        }
        for r in results
    ]


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
