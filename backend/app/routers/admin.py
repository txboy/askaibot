import json
import os
import shutil
import uuid
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import mcp as mcp_core
from .. import skills as skill_core
from .. import models, schemas
from ..auth import create_admin_token, get_current_admin
from ..common import get_setting, mask_key
from ..config import config
from ..kb import retrieve_kb
from ..database import get_db
from ..security import hash_password, verify_password

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=schemas.AdminLoginResponse)
def admin_login(payload: schemas.AdminLoginRequest, db: Session = Depends(get_db)):
    admin = (
        db.query(models.Admin).filter(models.Admin.username == payload.username).first()
    )
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return schemas.AdminLoginResponse(token=create_admin_token(admin.username))


def _endpoint_out(e: models.ApiEndpoint) -> schemas.EndpointOut:
    return schemas.EndpointOut(
        id=e.id,
        name=e.name,
        base_url=e.base_url,
        api_key_masked=mask_key(e.api_key),
        models=e.models,
        enabled=e.enabled,
        is_default=e.is_default,
    )


@router.get("/endpoints", response_model=list[schemas.EndpointOut])
def list_endpoints(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_endpoint_out(e) for e in db.query(models.ApiEndpoint).all()]


@router.post("/endpoints", response_model=schemas.EndpointOut)
def create_endpoint(
    payload: schemas.EndpointCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = models.ApiEndpoint(
        name=payload.name,
        base_url=payload.base_url,
        api_key=payload.api_key or "",
        models=payload.models or "",
        enabled=payload.enabled or 1,
        is_default=payload.is_default or 0,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


@router.get("/endpoints/usage")
def endpoints_usage(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    today_start = datetime.combine(datetime.now().date(), time.min)
    month_start = datetime(datetime.now().year, datetime.now().month, 1)
    result = []
    for e in db.query(models.ApiEndpoint).all():
        total = (
            db.query(func.coalesce(func.sum(models.Message.tokens), 0))
            .filter(models.Message.endpoint_id == e.id)
            .scalar()
        )
        today = (
            db.query(func.coalesce(func.sum(models.Message.tokens), 0))
            .filter(
                models.Message.endpoint_id == e.id,
                models.Message.created_at >= today_start,
            )
            .scalar()
        )
        month = (
            db.query(func.coalesce(func.sum(models.Message.tokens), 0))
            .filter(
                models.Message.endpoint_id == e.id,
                models.Message.created_at >= month_start,
            )
            .scalar()
        )
        result.append(
            {
                "id": e.id,
                "name": e.name,
                "base_url": e.base_url,
                "is_default": e.is_default,
                "enabled": e.enabled,
                "today_tokens": today,
                "month_tokens": month,
                "total_tokens": total,
            }
        )
    return result


@router.put("/endpoints/{endpoint_id}", response_model=schemas.EndpointOut)
def update_endpoint(
    endpoint_id: int,
    payload: schemas.EndpointUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = db.get(models.ApiEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    if payload.name is not None:
        endpoint.name = payload.name
    if payload.base_url is not None:
        endpoint.base_url = payload.base_url
    if payload.api_key:
        endpoint.api_key = payload.api_key
    if payload.models is not None:
        endpoint.models = payload.models
    if payload.enabled is not None:
        endpoint.enabled = payload.enabled
    if payload.is_default is not None:
        endpoint.is_default = payload.is_default
        if payload.is_default:
            db.query(models.ApiEndpoint).filter(
                models.ApiEndpoint.id != endpoint.id
            ).update({"is_default": 0})
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


@router.delete("/endpoints/{endpoint_id}")
def delete_endpoint(
    endpoint_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    endpoint = db.get(models.ApiEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    db.delete(endpoint)
    db.commit()
    return {"ok": True}


@router.get("/wecom", response_model=schemas.WecomOut)
def get_wecom(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return schemas.WecomOut(
        wecom_corp_id=setting.wecom_corp_id,
        wecom_agent_id=setting.wecom_agent_id,
        wecom_redirect=setting.wecom_redirect,
        wecom_secret_set=bool(setting.wecom_secret),
    )


@router.put("/wecom", response_model=schemas.WecomOut)
def update_wecom(
    payload: schemas.WecomUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.wecom_corp_id is not None:
        setting.wecom_corp_id = payload.wecom_corp_id
    if payload.wecom_secret:
        setting.wecom_secret = payload.wecom_secret
    if payload.wecom_agent_id is not None:
        setting.wecom_agent_id = payload.wecom_agent_id
    if payload.wecom_redirect is not None:
        setting.wecom_redirect = payload.wecom_redirect
    db.commit()
    db.refresh(setting)
    return schemas.WecomOut(
        wecom_corp_id=setting.wecom_corp_id,
        wecom_agent_id=setting.wecom_agent_id,
        wecom_redirect=setting.wecom_redirect,
        wecom_secret_set=bool(setting.wecom_secret),
    )


def _dingtalk_out(setting: models.Setting) -> schemas.DingtalkOut:
    return schemas.DingtalkOut(
        app_key=setting.dingtalk_app_key or "",
        agent_id=setting.dingtalk_agent_id or "",
        redirect=setting.dingtalk_redirect or "",
        app_secret_set=bool(setting.dingtalk_app_secret),
    )


@router.get("/dingtalk", response_model=schemas.DingtalkOut)
def get_dingtalk(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _dingtalk_out(get_setting(db))


@router.put("/dingtalk", response_model=schemas.DingtalkOut)
def update_dingtalk(
    payload: schemas.DingtalkUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.app_key is not None:
        setting.dingtalk_app_key = payload.app_key
    if payload.app_secret:
        setting.dingtalk_app_secret = payload.app_secret
    if payload.agent_id is not None:
        setting.dingtalk_agent_id = payload.agent_id
    if payload.redirect is not None:
        setting.dingtalk_redirect = payload.redirect
    db.commit()
    db.refresh(setting)
    return _dingtalk_out(setting)


def _feishu_out(setting: models.Setting) -> schemas.FeishuOut:
    return schemas.FeishuOut(
        app_id=setting.feishu_app_id or "",
        redirect=setting.feishu_redirect or "",
        app_secret_set=bool(setting.feishu_app_secret),
    )


@router.get("/feishu", response_model=schemas.FeishuOut)
def get_feishu(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _feishu_out(get_setting(db))


@router.put("/feishu", response_model=schemas.FeishuOut)
def update_feishu(
    payload: schemas.FeishuUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.app_id is not None:
        setting.feishu_app_id = payload.app_id
    if payload.app_secret:
        setting.feishu_app_secret = payload.app_secret
    if payload.redirect is not None:
        setting.feishu_redirect = payload.redirect
    db.commit()
    db.refresh(setting)
    return _feishu_out(setting)


@router.get("/search", response_model=schemas.SearchOut)
def get_search(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return schemas.SearchOut(
        provider=setting.search_provider,
        base_url=setting.search_base_url,
        auto=bool(setting.search_auto),
        api_key_set=bool(setting.search_api_key),
    )


@router.put("/search", response_model=schemas.SearchOut)
def update_search(
    payload: schemas.SearchUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.provider is not None:
        setting.search_provider = payload.provider
    if payload.api_key:
        setting.search_api_key = payload.api_key
    if payload.base_url is not None:
        setting.search_base_url = payload.base_url
    if payload.auto is not None:
        setting.search_auto = 1 if payload.auto else 0
    db.commit()
    db.refresh(setting)
    return schemas.SearchOut(
        provider=setting.search_provider,
        base_url=setting.search_base_url,
        auto=bool(setting.search_auto),
        api_key_set=bool(setting.search_api_key),
    )


def _sms_out(setting: models.Setting) -> schemas.SmsOut:
    return schemas.SmsOut(
        provider=setting.sms_provider or "",
        access_key_id=setting.sms_access_key_id or "",
        sign_name=setting.sms_sign_name or "",
        template_code=setting.sms_template_code or "",
        region=setting.sms_region or "",
        sdk_app_id=setting.sms_sdk_app_id or "",
        secret_set=bool(setting.sms_secret),
    )


@router.get("/sms", response_model=schemas.SmsOut)
def get_sms(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _sms_out(get_setting(db))


@router.put("/sms", response_model=schemas.SmsOut)
def update_sms(
    payload: schemas.SmsUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.provider is not None:
        setting.sms_provider = payload.provider
    if payload.access_key_id is not None:
        setting.sms_access_key_id = payload.access_key_id
    if payload.secret:
        setting.sms_secret = payload.secret
    if payload.sign_name is not None:
        setting.sms_sign_name = payload.sign_name
    if payload.template_code is not None:
        setting.sms_template_code = payload.template_code
    if payload.region is not None:
        setting.sms_region = payload.region
    if payload.sdk_app_id is not None:
        setting.sms_sdk_app_id = payload.sdk_app_id
    db.commit()
    db.refresh(setting)
    return _sms_out(setting)


def _kb_out(kb: models.KnowledgeBase) -> schemas.KnowledgeBaseOut:
    return schemas.KnowledgeBaseOut(
        id=kb.id,
        name=kb.name,
        provider=kb.provider,
        base_url=kb.base_url,
        api_key_masked=mask_key(kb.api_key),
        dataset_ids=kb.dataset_ids,
        top_k=kb.top_k,
        mode=kb.mode,
        description=kb.description,
        enabled=kb.enabled,
    )


@router.get("/knowledge-bases", response_model=list[schemas.KnowledgeBaseOut])
def list_knowledge_bases(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_kb_out(kb) for kb in db.query(models.KnowledgeBase).all()]


@router.post("/knowledge-bases", response_model=schemas.KnowledgeBaseOut)
def create_knowledge_base(
    payload: schemas.KnowledgeBaseCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = models.KnowledgeBase(
        name=payload.name,
        provider=payload.provider or "dify",
        base_url=payload.base_url,
        api_key=payload.api_key or "",
        dataset_ids=payload.dataset_ids or "",
        top_k=payload.top_k or 5,
        mode=payload.mode or "frontend",
        description=payload.description or "",
        enabled=payload.enabled or 1,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _kb_out(kb)


@router.put("/knowledge-bases/{kb_id}", response_model=schemas.KnowledgeBaseOut)
def update_knowledge_base(
    kb_id: int,
    payload: schemas.KnowledgeBaseUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if payload.name is not None:
        kb.name = payload.name
    if payload.provider is not None:
        kb.provider = payload.provider
    if payload.base_url is not None:
        kb.base_url = payload.base_url
    if payload.api_key:
        kb.api_key = payload.api_key
    if payload.dataset_ids is not None:
        kb.dataset_ids = payload.dataset_ids
    if payload.top_k is not None:
        kb.top_k = payload.top_k
    if payload.mode is not None:
        kb.mode = payload.mode
    if payload.description is not None:
        kb.description = payload.description
    if payload.enabled is not None:
        kb.enabled = payload.enabled
    db.commit()
    db.refresh(kb)
    return _kb_out(kb)


@router.delete("/knowledge-bases/{kb_id}")
def delete_knowledge_base(
    kb_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    db.delete(kb)
    db.commit()
    return {"ok": True}


@router.post("/knowledge-bases/test", response_model=dict)
async def test_knowledge_base(
    payload: schemas.KnowledgeBaseTestRequest,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    results = await retrieve_kb(
        payload.provider,
        payload.base_url,
        payload.api_key,
        payload.dataset_ids,
        payload.query,
        top_k=payload.top_k,
    )
    return {"ok": True, "count": len(results), "results": results}


def _bot_callback_url(db: Session, bot_id: int, provider: str = "wecom") -> str:
    if provider == "dingtalk":
        base = (get_setting(db).dingtalk_redirect or config.frontend_url).rstrip("/")
        return f"{base}/api/dingtalk/bot/{bot_id}/callback"
    if provider == "feishu":
        base = (get_setting(db).feishu_redirect or config.frontend_url).rstrip("/")
        return f"{base}/api/feishu/bot/{bot_id}/callback"
    base = (get_setting(db).wecom_redirect or config.frontend_url).rstrip("/")
    return f"{base}/api/wecom/bot/{bot_id}/callback"


def _bot_out(bot: models.WecomBot, db: Session) -> schemas.WecomBotOut:
    return schemas.WecomBotOut(
        id=bot.id,
        name=bot.name,
        provider=bot.provider,
        corp_id=bot.corp_id,
        agent_id=bot.agent_id,
        token_masked=mask_key(bot.token),
        aes_key_set=bool(bot.aes_key),
        kb_ids=bot.kb_ids,
        mcp_ids=bot.mcp_ids,
        skill_ids=bot.skill_ids,
        web_search=bot.web_search,
        endpoint_id=bot.endpoint_id,
        model=bot.model,
        enabled=bot.enabled,
        callback_url=_bot_callback_url(db, bot.id, bot.provider),
    )


@router.get("/wecom-bots", response_model=list[schemas.WecomBotOut])
def list_wecom_bots(
    provider: str = "wecom",
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.WecomBot)
    if provider:
        q = q.filter(models.WecomBot.provider == provider)
    return [_bot_out(b, db) for b in q.all()]


@router.post("/wecom-bots", response_model=schemas.WecomBotOut)
def create_wecom_bot(
    payload: schemas.WecomBotCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bot = models.WecomBot(
        name=payload.name,
        provider=payload.provider or "wecom",
        corp_id=payload.corp_id or "",
        secret=payload.secret or "",
        agent_id=payload.agent_id or "",
        token=payload.token or "",
        aes_key=payload.aes_key or "",
        kb_ids=payload.kb_ids or "",
        mcp_ids=payload.mcp_ids or "",
        web_search=payload.web_search or 0,
        endpoint_id=payload.endpoint_id,
        model=payload.model or "",
        enabled=payload.enabled or 1,
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return _bot_out(bot, db)


@router.put("/wecom-bots/{bot_id}", response_model=schemas.WecomBotOut)
def update_wecom_bot(
    bot_id: int,
    payload: schemas.WecomBotUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bot = db.get(models.WecomBot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    for field in (
        "name",
        "provider",
        "corp_id",
        "agent_id",
        "token",
        "aes_key",
        "kb_ids",
        "mcp_ids",
        "model",
    ):
        val = getattr(payload, field)
        if val is not None:
            setattr(bot, field, val)
    if payload.secret:
        bot.secret = payload.secret
    if payload.web_search is not None:
        bot.web_search = payload.web_search
    if payload.endpoint_id is not None:
        bot.endpoint_id = payload.endpoint_id
    if payload.enabled is not None:
        bot.enabled = payload.enabled
    db.commit()
    db.refresh(bot)
    return _bot_out(bot, db)


@router.delete("/wecom-bots/{bot_id}")
def delete_wecom_bot(
    bot_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bot = db.get(models.WecomBot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    db.delete(bot)
    db.commit()
    return {"ok": True}


_SECRET_HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "token",
    "key",
    "secret",
    "x-auth-token",
}


def _mask_headers(headers) -> dict:
    out: dict = {}
    if not isinstance(headers, dict):
        return out
    for k, v in headers.items():
        if k.lower() in _SECRET_HEADER_KEYS:
            out[k] = mask_key(str(v))
        else:
            out[k] = v
    return out


def _mcp_out(server: models.McpServer) -> schemas.McpServerOut:
    tools = [
        schemas.McpToolOut(
            name=t["name"],
            description=t.get("description") or "",
            input_schema=t.get("input_schema") or {},
        )
        for t in (mcp_core.get_cached_tools(server.id) or [])
    ]
    headers = {}
    try:
        parsed = json.loads(server.headers or "{}")
        if isinstance(parsed, dict):
            headers = parsed
    except Exception:
        headers = {}
    return schemas.McpServerOut(
        id=server.id,
        name=server.name,
        description=server.description,
        transport=server.transport,
        url=server.url,
        headers_masked=str(_mask_headers(headers)),
        command=server.command,
        args=server.args,
        env_set=bool(server.env and server.env != "{}"),
        mode=server.mode,
        enabled=server.enabled,
        tools=tools,
    )


@router.get("/mcp", response_model=list[schemas.McpServerOut])
def list_mcp_servers(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_mcp_out(s) for s in db.query(models.McpServer).all()]


@router.post("/mcp", response_model=schemas.McpServerOut)
def create_mcp_server(
    payload: schemas.McpServerCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = models.McpServer(
        name=payload.name,
        description=payload.description or "",
        transport=payload.transport or "http",
        url=payload.url or "",
        headers=payload.headers or "{}",
        command=payload.command or "",
        args=payload.args or "[]",
        env=payload.env or "{}",
        mode=payload.mode or "llm",
        enabled=payload.enabled or 1,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return _mcp_out(server)


@router.put("/mcp/{server_id}", response_model=schemas.McpServerOut)
def update_mcp_server(
    server_id: int,
    payload: schemas.McpServerUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    for field in (
        "name",
        "description",
        "transport",
        "url",
        "headers",
        "command",
        "args",
        "env",
        "mode",
    ):
        val = getattr(payload, field)
        if val is not None:
            setattr(server, field, val)
    if payload.enabled is not None:
        server.enabled = payload.enabled
    db.commit()
    db.refresh(server)
    mcp_core.clear_cache(server.id)
    return _mcp_out(server)


@router.delete("/mcp/{server_id}")
def delete_mcp_server(
    server_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    db.delete(server)
    db.commit()
    mcp_core.clear_cache(server.id)
    return {"ok": True}


@router.post("/mcp/{server_id}/test", response_model=list[schemas.McpToolOut])
async def test_mcp_server(
    server_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    try:
        tools = await mcp_core.list_tools(server)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"连接失败：{exc}")
    return [
        schemas.McpToolOut(
            name=t["name"],
            description=t.get("description") or "",
            input_schema=t.get("input_schema") or {},
        )
        for t in tools
    ]


@router.post("/mcp/{server_id}/refresh", response_model=list[schemas.McpToolOut])
async def refresh_mcp_server(
    server_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    server = db.get(models.McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    mcp_core.clear_cache(server.id)
    try:
        tools = await mcp_core.list_tools(server)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"连接失败：{exc}")
    return [
        schemas.McpToolOut(
            name=t["name"],
            description=t.get("description") or "",
            input_schema=t.get("input_schema") or {},
        )
        for t in tools
    ]


@router.get("/stats")
def stats(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total_tokens = db.query(func.coalesce(func.sum(models.Message.tokens), 0)).scalar()
    today_start = datetime.combine(datetime.now().date(), time.min)
    today_tokens = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .filter(models.Message.created_at >= today_start)
        .scalar()
    )
    month_start = datetime(datetime.now().year, datetime.now().month, 1)
    month_tokens = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .filter(models.Message.created_at >= month_start)
        .scalar()
    )
    return {
        "users": db.query(models.User).count(),
        "conversations": db.query(models.Conversation).count(),
        "messages": db.query(models.Message).count(),
        "endpoints": db.query(models.ApiEndpoint).count(),
        "attachments": db.query(models.Attachment).count(),
        "total_tokens": total_tokens,
        "today_tokens": today_tokens,
        "month_tokens": month_tokens,
    }


@router.get("/system", response_model=schemas.SystemOut)
def get_system(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return schemas.SystemOut(
        site_title=setting.site_title or "askai",
        theme=setting.theme,
        debug_mode=bool(setting.debug_mode),
        favicon_set=bool(setting.favicon_path),
        admin_secret_enabled=bool(setting.admin_secret_enabled),
        admin_secret=setting.admin_secret,
        assistant_name=setting.assistant_name or "askai",
        assistant_avatar_set=bool(setting.assistant_avatar),
    )


@router.put("/system", response_model=schemas.SystemOut)
def update_system(
    payload: schemas.SystemUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if payload.site_title is not None:
        setting.site_title = payload.site_title
    if payload.admin_secret_enabled is not None:
        setting.admin_secret_enabled = 1 if payload.admin_secret_enabled else 0
    if payload.admin_secret is not None:
        setting.admin_secret = payload.admin_secret
    if payload.assistant_name is not None:
        setting.assistant_name = payload.assistant_name.strip() or "askai"
    db.commit()
    db.refresh(setting)
    return schemas.SystemOut(
        site_title=setting.site_title,
        theme=setting.theme,
        debug_mode=bool(setting.debug_mode),
        favicon_set=bool(setting.favicon_path),
        admin_secret_enabled=bool(setting.admin_secret_enabled),
        admin_secret=setting.admin_secret,
        assistant_name=setting.assistant_name or "askai",
        assistant_avatar_set=bool(setting.assistant_avatar),
    )


@router.get("/theme")
def admin_get_theme(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return {"theme": get_setting(db).theme}


@router.put("/theme")
def admin_save_theme(
    payload: schemas.ThemeUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    setting.theme = payload.theme
    db.commit()
    db.refresh(setting)
    return {"theme": setting.theme}


@router.get("/debug")
def admin_get_debug(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return {"debug_mode": bool(get_setting(db).debug_mode)}


@router.put("/debug")
def admin_save_debug(
    payload: schemas.DebugUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    setting.debug_mode = 1 if payload.debug_mode else 0
    db.commit()
    db.refresh(setting)
    return {"debug_mode": bool(setting.debug_mode)}


@router.get("/access")
def admin_access(r: str = "", db: Session = Depends(get_db)):
    setting = get_setting(db)
    if setting.admin_secret_enabled:
        if r != setting.admin_secret:
            raise HTTPException(status_code=404, detail="页面不存在")
    return {"ok": True}


@router.post("/favicon")
async def upload_favicon(
    file: UploadFile = File(...),
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Favicon 文件过大")
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    os.makedirs(config.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "favicon")[1].lower() or ".ico"
    stored = f"favicon_{uuid.uuid4().hex}{ext}"
    path = os.path.join(config.upload_dir, stored)
    with open(path, "wb") as f:
        f.write(data)

    setting = get_setting(db)
    if setting.favicon_path:
        old = os.path.join(config.upload_dir, setting.favicon_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    setting.favicon_path = stored
    db.commit()
    return {"favicon_set": True, "url": "/api/favicon"}


@router.delete("/favicon")
def delete_favicon(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if setting.favicon_path:
        old = os.path.join(config.upload_dir, setting.favicon_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
        setting.favicon_path = ""
        db.commit()
    return {"favicon_set": False}


@router.post("/assistant-avatar")
async def upload_assistant_avatar(
    file: UploadFile = File(...),
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片文件过大")
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    os.makedirs(config.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "assistant_avatar")[1].lower()
    stored = f"assistant_avatar_{uuid.uuid4().hex}{ext}"
    path = os.path.join(config.upload_dir, stored)
    with open(path, "wb") as f:
        f.write(data)

    setting = get_setting(db)
    if setting.assistant_avatar:
        old = os.path.join(config.upload_dir, setting.assistant_avatar)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    setting.assistant_avatar = stored
    db.commit()
    return {"assistant_avatar_set": True, "url": "/api/assistant-avatar"}


@router.delete("/assistant-avatar")
def delete_assistant_avatar(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if setting.assistant_avatar:
        old = os.path.join(config.upload_dir, setting.assistant_avatar)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
        setting.assistant_avatar = ""
        db.commit()
    return {"assistant_avatar_set": False}


@router.get("/logo")
def logo_status(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    return {"logo_set": bool(setting.logo_path)}


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo 文件过大")
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    os.makedirs(config.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "logo")[1].lower() or ".png"
    stored = f"logo_{uuid.uuid4().hex}{ext}"
    path = os.path.join(config.upload_dir, stored)
    with open(path, "wb") as f:
        f.write(data)

    setting = get_setting(db)
    if setting.logo_path:
        old = os.path.join(config.upload_dir, setting.logo_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    setting.logo_path = stored
    db.commit()
    return {"logo_set": True, "url": "/api/logo"}


@router.delete("/logo")
def delete_logo(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    if setting.logo_path:
        old = os.path.join(config.upload_dir, setting.logo_path)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
        setting.logo_path = ""
        db.commit()
    return {"logo_set": False}


def _user_out(db: Session, u: models.User) -> schemas.AdminUserOut:
    today_start = datetime.combine(datetime.now().date(), time.min)
    conv_count = (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == u.id)
        .count()
    )
    joined = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .join(
            models.Conversation,
            models.Message.conversation_id == models.Conversation.id,
        )
        .filter(models.Conversation.user_id == u.id)
    )
    total = joined.scalar()
    today = joined.filter(models.Message.created_at >= today_start).scalar()
    last_active = (
        db.query(func.max(models.Message.created_at))
        .join(
            models.Conversation,
            models.Message.conversation_id == models.Conversation.id,
        )
        .filter(models.Conversation.user_id == u.id)
        .scalar()
    )
    return schemas.AdminUserOut(
        id=u.id,
        nickname=u.nickname,
        phone=u.phone,
        created_at=u.created_at,
        conversation_count=conv_count,
        last_active=last_active,
        total_tokens=total,
        today_tokens=today,
    )


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [_user_out(db, u) for u in users]


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    conv_ids = [
        c.id
        for c in db.query(models.Conversation)
        .filter(models.Conversation.user_id == user.id)
        .all()
    ]
    attachments = (
        db.query(models.Attachment).filter(models.Attachment.user_id == user.id).all()
    )
    for att in attachments:
        old = os.path.join(config.upload_dir, att.stored_name)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
    if conv_ids:
        db.query(models.Message).filter(
            models.Message.conversation_id.in_(conv_ids)
        ).delete(synchronize_session=False)
    db.query(models.Attachment).filter(models.Attachment.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(models.Conversation).filter(models.Conversation.user_id == user.id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.put("/password")
def change_password(
    payload: schemas.AdminPasswordChange,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    admin.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}


def _skill_out(skill: models.Skill, db: Session) -> schemas.SkillOut:
    try:
        tools = json.loads(skill.tools or "[]")
    except Exception:
        tools = []
    if not isinstance(tools, list):
        tools = []
    user_ids = [
        a.user_id
        for a in db.query(models.SkillAccess)
        .filter(models.SkillAccess.skill_id == skill.id)
        .all()
    ]
    return schemas.SkillOut(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        scope=skill.scope,
        enabled=skill.enabled,
        tools=[
            schemas.SkillToolOut(
                name=t.get("name", ""),
                description=t.get("description") or "",
                command=t.get("command") or "",
                input_schema=t.get("input_schema") or {},
            )
            for t in tools
        ],
        user_ids=user_ids,
    )


@router.get("/skills", response_model=list[schemas.SkillOut])
def list_skills(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return [_skill_out(s, db) for s in db.query(models.Skill).all()]


@router.post("/skills", response_model=schemas.SkillOut)
async def create_skill(
    file: UploadFile = File(...),
    scope: str = Form("global"),
    enabled: int = Form(1),
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if scope not in ("global", "user"):
        scope = "global"
    skills_base = os.path.join(config.upload_dir, "skills")
    os.makedirs(skills_base, exist_ok=True)
    tmp_zip = os.path.join(skills_base, f"_upload_{uuid.uuid4().hex}.zip")
    tmp_dir = os.path.join(skills_base, f".tmp_{uuid.uuid4().hex}")
    try:
        content = await file.read()
        with open(tmp_zip, "wb") as fh:
            fh.write(content)
        try:
            skill_core.extract_upload(tmp_zip, tmp_dir)
            info = skill_core.parse_skill(tmp_dir)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"技能包解析失败：{exc}")
        skill = models.Skill(
            name=info["name"],
            description=info["description"],
            dir_path=tmp_dir,
            content=info["content"],
            tools=json.dumps(info["tools"], ensure_ascii=False),
            scope=scope,
            enabled=enabled,
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)
        final_dir = os.path.join(skills_base, str(skill.id))
        if os.path.isdir(final_dir):
            shutil.rmtree(final_dir, ignore_errors=True)
        shutil.move(tmp_dir, final_dir)
        tmp_dir = final_dir
        skill.dir_path = final_dir
        db.commit()
        db.refresh(skill)
        return _skill_out(skill, db)
    finally:
        if os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except OSError:
                pass
        if os.path.isdir(tmp_dir) and not os.path.exists(
            os.path.join(tmp_dir, "SKILL.md")
        ):
            shutil.rmtree(tmp_dir, ignore_errors=True)


@router.put("/skills/{skill_id}", response_model=schemas.SkillOut)
def update_skill(
    skill_id: int,
    payload: schemas.SkillUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    skill = db.get(models.Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    if payload.name is not None:
        skill.name = payload.name
    if payload.description is not None:
        skill.description = payload.description
    if payload.scope is not None:
        if payload.scope not in ("global", "user"):
            raise HTTPException(status_code=400, detail="scope 仅支持 global/user")
        skill.scope = payload.scope
    if payload.enabled is not None:
        skill.enabled = payload.enabled
    if payload.user_ids is not None:
        db.query(models.SkillAccess).filter(
            models.SkillAccess.skill_id == skill.id
        ).delete()
        for uid in payload.user_ids:
            db.add(models.SkillAccess(skill_id=skill.id, user_id=uid))
    db.commit()
    db.refresh(skill)
    return _skill_out(skill, db)


@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    skill = db.get(models.Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    if skill.dir_path:
        shutil.rmtree(skill.dir_path, ignore_errors=True)
    db.query(models.SkillAccess).filter(
        models.SkillAccess.skill_id == skill.id
    ).delete()
    db.delete(skill)
    db.commit()
    return {"ok": True}


@router.post("/skills/{skill_id}/test")
async def test_skill(
    skill_id: int,
    payload: schemas.SkillTestRequest,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    skill = db.get(models.Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    try:
        tools = json.loads(skill.tools or "[]")
    except Exception:
        tools = []
    if not isinstance(tools, list):
        tools = []
    tool = next(
        (t for t in tools if isinstance(t, dict) and t.get("name") == payload.tool),
        None,
    )
    if not tool:
        raise HTTPException(status_code=400, detail=f"技能中不存在工具：{payload.tool}")
    try:
        output = await skill_core.call_tool(skill, tool, payload.args or {})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"执行失败：{exc}")
    return {"output": output}
