"""飞书机器人核心：tenant_access_token 缓存与文本消息发送。"""

import json
import time

import httpx


_token_cache: dict[str, tuple[str, float]] = {}


async def get_access_token(app_id: str, app_secret: str) -> str:
    cache_key = f"{app_id}:{app_secret}"
    entry = _token_cache.get(cache_key)
    if entry and entry[1] > time.time():
        return entry[0]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
        )
        data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"获取飞书 tenant_access_token 失败：code={data.get('code')} msg={data.get('msg')}"
        )
    token = data["tenant_access_token"]
    expires = data.get("expire", 7200) - 300
    _token_cache[cache_key] = (token, time.time() + expires)
    return token


async def send_text(open_id: str, content: str, app_id: str, app_secret: str) -> None:
    token = await get_access_token(app_id, app_secret)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            params={"receive_id_type": "open_id"},
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": open_id,
                "msg_type": "text",
                "content": json.dumps({"text": content}, ensure_ascii=False),
            },
        )
        data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"发送飞书消息失败：code={data.get('code')} msg={data.get('msg')}"
        )
