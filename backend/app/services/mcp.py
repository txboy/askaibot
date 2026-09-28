"""MCP 工具集成：连接 MCP 服务器（HTTP / stdio）、列出与调用工具，并转换为 OpenAI function schema。

工具在后台以「服务」为单位管理。聊天时按需连接服务器列出工具，
将工具转换为 function 调用，模型自主决定是否调用；工具名以 ``mcp__`` 前缀命名空间化，
便于在请求内把模型的调用路由回对应的 MCP 服务器与工具。
"""

import json
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from app import models

# 工具名前缀，用于在函数调用层命名空间化（避免不同服务器重名）
PREFIX = "mcp__"
_TOOL_CACHE_TTL = 300  # 工具列表缓存 5 分钟

# server_id -> (cached_at, tools)
_tool_cache: dict[int, tuple[float, list[dict]]] = {}


def _slug(name: str) -> str:
    out = []
    for ch in name or "":
        out.append(ch if (ch.isalnum() or ch == "-") else "_")
    return "".join(out).strip("_") or "mcp"


def function_name(server_name: str, tool_name: str) -> str:
    return f"{PREFIX}{_slug(server_name)}__{_slug(tool_name)}"


def _parse_json(value: str, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


@asynccontextmanager
async def _connect(server: models.McpServer) -> AsyncIterator[ClientSession]:
    """按传输方式连接 MCP 服务器并返回已初始化的 ClientSession。"""
    if (server.transport or "").lower() == "stdio":
        params = StdioServerParameters(
            command=server.command,
            args=_parse_json(server.args, []) or [],
            env=_parse_json(server.env, {}) or None,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        parsed = _parse_json(server.headers, {})
        headers = parsed if isinstance(parsed, dict) else {}
        client = httpx.AsyncClient(headers=headers, timeout=30)
        try:
            async with streamable_http_client(server.url, http_client=client) as (
                read,
                write,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        finally:
            await client.aclose()


def _tool_to_dict(tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.input_schema or {"type": "object", "properties": {}},
    }


async def _fetch_tools(server: models.McpServer) -> list[dict]:
    async with _connect(server) as session:
        result = await session.list_tools()
        return [_tool_to_dict(t) for t in result.tools]


def clear_cache(server_id: int | None = None) -> None:
    if server_id is None:
        _tool_cache.clear()
    else:
        _tool_cache.pop(server_id, None)


def get_cached_tools(server_id: int) -> list[dict] | None:
    """读取缓存中的工具列表（不触发网络请求），未缓存返回 None。"""
    entry = _tool_cache.get(server_id)
    if entry and time.time() - entry[0] < _TOOL_CACHE_TTL:
        return list(entry[1])
    return None


async def list_tools(server: models.McpServer) -> list[dict]:
    """列出 MCP 服务器暴露的工具（带内存缓存）。"""
    entry = _tool_cache.get(server.id)
    if entry and time.time() - entry[0] < _TOOL_CACHE_TTL:
        return list(entry[1])
    tools = await _fetch_tools(server)
    _tool_cache[server.id] = (time.time(), list(tools))
    return tools


def _extract_text(result) -> str:
    parts: list[str] = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts) if parts else ""


async def call_tool(
    server: models.McpServer, tool_name: str, arguments: dict | None
) -> str:
    """调用 MCP 工具并返回文本结果。"""
    async with _connect(server) as session:
        result = await session.call_tool(tool_name, arguments or {})
        return _extract_text(result)


async def build_openai_tools(
    servers: list[models.McpServer],
) -> tuple[list[dict], dict[str, tuple[models.McpServer, str]]]:
    """把一组 MCP 服务器转换为 OpenAI function tools，并返回 名称->(server, tool) 映射用于路由。"""
    openai_tools: list[dict] = []
    mapping: dict[str, tuple[models.McpServer, str]] = {}
    for server in servers:
        try:
            tools = await list_tools(server)
        except Exception:
            continue
        for t in tools:
            name = function_name(server.name, t["name"])
            mapping[name] = (server, t["name"])
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": t.get("description") or "",
                        "parameters": t.get("input_schema")
                        or {"type": "object", "properties": {}},
                    },
                }
            )
    return openai_tools, mapping


def parse_ids(ids: str) -> list[int]:
    return [int(x) for x in (ids or "").split(",") if x.strip().isdigit()]


def resolve_servers(
    db, server_ids: list[int], mode: str | None = None
) -> list[models.McpServer]:
    """按 id 列表（可选按 mode 过滤）加载已启用的 MCP 服务器。"""
    if not server_ids:
        return []
    query = db.query(models.McpServer).filter(
        models.McpServer.id.in_(server_ids),
        models.McpServer.enabled == 1,
    )
    if mode is not None:
        query = query.filter(models.McpServer.mode == mode)
    return query.all()


def all_servers(db, mode: str | None = None) -> list[models.McpServer]:
    query = db.query(models.McpServer).filter(models.McpServer.enabled == 1)
    if mode is not None:
        query = query.filter(models.McpServer.mode == mode)
    return query.all()
