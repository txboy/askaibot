"""钉钉机器人核心：access_token 缓存与文本消息发送。"""

import json
import time

import httpx


_token_cache: dict[str, tuple[str, float]] = {}


async def get_access_token(app_key: str, app_secret: str) -> str:
    cache_key = f"{app_key}:{app_secret}"
    entry = _token_cache.get(cache_key)
    if entry and entry[1] > time.time():
        return entry[0]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://oapi.dingtalk.com/gettoken",
            params={"appkey": app_key, "appsecret": app_secret},
        )
        data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(
            f"获取钉钉 access_token 失败：errcode={data.get('errcode')} errmsg={data.get('errmsg')}"
        )
    token = data["access_token"]
    expires = data.get("expires_in", 7200) - 300
    _token_cache[cache_key] = (token, time.time() + expires)
    return token


async def resolve_userid_by_unionid(app_key: str, app_secret: str, unionid: str) -> str:
    """通过 unionId 获取组织内 userId（需服务端 corp access_token + 通讯录读权限）。"""
    token = await get_access_token(app_key, app_secret)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://oapi.dingtalk.com/topapi/v2/user/getbyunionid",
            params={"access_token": token},
            json={"unionid": unionid},
        )
        data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(
            f"通过 unionId 获取 userId 失败：errcode={data.get('errcode')} errmsg={data.get('errmsg')}"
        )
    userid = (data.get("result") or {}).get("userid")
    if not userid:
        raise RuntimeError(f"通过 unionId 获取 userId 失败：result 为空 {data}")
    return userid


async def send_text(
    userid: str, content: str, agent_id: str, app_key: str, app_secret: str
) -> None:
    token = await get_access_token(app_key, app_secret)
    hi = {"msgtype": "text", "text": {"content": content}}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2",
            params={"access_token": token},
            json={
                "agent_id": int(agent_id),
                "userid_list": userid,
                "msg": json.dumps(hi, ensure_ascii=False),
            },
        )
        data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(
            f"发送钉钉消息失败：errcode={data.get('errcode')} errmsg={data.get('errmsg')}"
        )
