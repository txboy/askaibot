"""联网搜索：根据后台配置的 provider 调用真实搜索接口。"""

import httpx


def build_web_search_tool() -> dict:
    """构造 web_search 函数工具定义，用于让模型发起联网搜索。"""
    return {
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


async def search_web(
    provider: str,
    api_key: str,
    base_url: str,
    query: str,
    max_results: int = 5,
) -> list[dict]:
    provider = (provider or "").lower()
    if provider == "tavily":
        return await _tavily(api_key, query, max_results)
    if provider == "bing":
        return await _bing(api_key, query, max_results)
    if provider == "searxng":
        return await _searxng(base_url, query, max_results)
    if provider == "duckduckgo":
        return await _duckduckgo(query, max_results)
    raise ValueError(f"不支持的搜索来源：{provider}")


async def _tavily(api_key: str, query: str, max_results: int) -> list[dict]:
    if not api_key:
        raise ValueError("Tavily 未配置 API Key")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in data.get("results", [])
    ]


async def _bing(api_key: str, query: str, max_results: int) -> list[dict]:
    if not api_key:
        raise ValueError("Bing 未配置 API Key")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.bing.microsoft.com/v7.0/search",
            params={"q": query, "count": max_results},
            headers={"Ocp-Apim-Subscription-Key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
    web = data.get("webPages", {}).get("value", [])
    return [
        {
            "title": r.get("name", ""),
            "url": r.get("url", ""),
            "content": r.get("snippet", ""),
        }
        for r in web
    ]


async def _searxng(base_url: str, query: str, max_results: int) -> list[dict]:
    base = (base_url or "").rstrip("/")
    if not base:
        raise ValueError("SearXNG 未配置地址")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{base}/search", params={"q": query, "format": "json"})
        resp.raise_for_status()
        data = resp.json()
    results = data.get("results", [])[:max_results]
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in results
    ]


async def _duckduckgo(query: str, max_results: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    results: list[dict] = []
    if data.get("AbstractText"):
        results.append(
            {
                "title": data.get("Heading", ""),
                "url": data.get("AbstractURL", ""),
                "content": data.get("AbstractText", ""),
            }
        )
    for topic in data.get("RelatedTopics", []):
        if "Topics" in topic:
            for sub in topic["Topics"]:
                if sub.get("Text") and len(results) < max_results:
                    results.append(
                        {
                            "title": sub["Text"][:60],
                            "url": sub.get("FirstURL", ""),
                            "content": sub["Text"],
                        }
                    )
        elif topic.get("Text") and len(results) < max_results:
            results.append(
                {
                    "title": topic["Text"][:60],
                    "url": topic.get("FirstURL", ""),
                    "content": topic["Text"],
                }
            )
    return results[:max_results]


def format_results(results: list[dict]) -> str:
    if not results:
        return "未找到相关网页结果。"
    lines = []
    for i, r in enumerate(results, 1):
        text = r["content"].strip()
        if len(text) > 500:
            text = text[:500] + "…"
        lines.append(f"{i}. {r['title']}\n   链接: {r['url']}\n   内容: {text}")
    return "以下是联网搜索结果，请基于这些信息回答用户的问题：\n\n" + "\n\n".join(lines)
