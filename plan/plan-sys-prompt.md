# 系统提示词（层级化）方案

> 目标：为机器人（企微/钉钉/飞书）与交互聊天引入**层级化系统提示词**，后台可分层配置，运行时按优先级取用。
> 优先级（高→低）：**机器人 > 基础配置（按平台）> 模型接口 > 通用配置**，取**第一个非空**者；顶层非空即用，不再回退。

## 背景

- 机器人流程 `wecom_bot.generate_reply()` 与交互聊天 `chat.py` 目前均**无系统提示词**，仅注入技能 `system` 内容与知识库上下文。
- 各实体归属：
  - `WecomBot`（机器人）：`provider = wecom/dingtalk/feishu`
  - `Setting`（全局）：含平台基础配置 `feishu_app_id` 等，用于 `admin/integrations.py`
  - `ApiEndpoint`（模型接口）：每接口可含多个模型名
  - `User`：`wecom_userid / dingtalk_userid / feishu_userid` 用于判定注册平台

## 数据模型 & 数据库迁移

| 层级 | 字段 | 表 |
|---|---|---|
| 通用 | `system_prompt` | `Setting` |
| 基础配置 | `wecom_system_prompt` / `dingtalk_system_prompt` / `feishu_system_prompt` | `Setting` |
| 模型接口 | `system_prompt` | `ApiEndpoint` |
| 机器人 | `system_prompt` | `WecomBot` |

字段统一用 `Text` 以支持长提示词。`main.py::_ensure_columns()` 为既有 `settings` / `wecom_bots` / `api_endpoints` 表补列（`ALTER TABLE ADD COLUMN ... TEXT DEFAULT ''`）。

## 核心解析函数（`app/common.py`）

```python
def resolve_system_prompt(db, bot=None, endpoint=None, provider=None) -> str:
    setting = get_setting(db)
    if bot and bot.system_prompt:                      # 机器人
        return bot.system_prompt
    prov = provider or (bot.provider if bot else None)
    if prov == "wecom" and setting.wecom_system_prompt:       # 基础配置（按平台）
        return setting.wecom_system_prompt
    if prov == "dingtalk" and setting.dingtalk_system_prompt:
        return setting.dingtalk_system_prompt
    if prov == "feishu" and setting.feishu_system_prompt:
        return setting.feishu_system_prompt
    if endpoint and endpoint.system_prompt:            # 模型接口
        return endpoint.system_prompt
    return setting.system_prompt or ""                 # 通用
```

## 用户注册平台判定（`app/common.py`）

```python
def user_platform(user) -> str:
    if user.feishu_userid:    return "feishu"
    if user.dingtalk_userid:  return "dingtalk"
    if user.wecom_userid:     return "wecom"
    return ""
```

## 注入点

- **机器人流程** `wecom_bot.py::generate_reply`：
  `prompt = resolve_system_prompt(db, bot=bot, endpoint=endpoint)`；非空则前置 `{"role":"system","content":prompt}`，置于技能 `system` 之前。
- **交互聊天** `chat.py`：
  `prompt = resolve_system_prompt(db, endpoint=endpoint, provider=user_platform(user))`；非空则前置 system 消息。
  - 用户有平台身份 → 用该平台基础提示词；
  - 否则（手机号/普通注册）→ 模型接口 > 通用。

## Schema / Controller

`schemas.py` 增加 `system_prompt` 字段：
- `WecomBotCreate / WecomBotUpdate / WecomBotOut`
- `EndpointCreate / EndpointUpdate / EndpointOut`
- `SystemOut / SystemUpdate`（通用，AdminSystem 页）
- `WecomOut / WecomUpdate / DingtalkOut / DingtalkUpdate / FeishuOut / FeishuUpdate`（平台基础配置页）

对应控制器读写：
- `admin/wecom_bots.py`（create/update/`_bot_out`）
- `admin/endpoints.py`（create/update/`_endpoint_out`）
- `admin/integrations.py`（wecom/dingtalk/feishu get/update）
- `admin/system.py`（get/update_system）

## 前端启动器（UI）

- `AdminSystem.vue`：新增「通用系统提示词」textarea，保存到 `/api/admin/system`。
- `AdminWecom.vue` / `AdminDingtalk.vue` / `AdminFeishu.vue`：基础配置卡片新增「系统提示词」textarea。
- `AdminEndpoints.vue`：接口表单新增「系统提示词」。
- `BotManager.vue`：机器人编辑弹窗新增「系统提示词」。
- `frontend/src/api.js`：相应接口调用带上 `system_prompt` 参数（若现为显式字段则补充）。

## 测试

- `tests/test_sys_prompt.py`：
  - `user_platform` 判定（feishu/dingtalk/wecom/普通用户）。
  - `resolve_system_prompt` 四层优先级全覆盖（仅顶层非空时不回退；空时下沉）。
- 调整 `tests/test_wecom_bot.py` / `tests/test_dingtalk_bot.py`：若已有「无 system 消息」断言，在未配置提示词时仍应成立。
- `tests/test_feishu_bot.py`：新增用例验证机器人流程前置的 system 消息来自解析结果。
- `tests/test_chat_search.py`（或新增）：聊天流程用例——平台用户命中对应 `xxx_system_prompt`，普通用户落到接口/通用。

## 验证

- `cd backend && python -m pytest -q`
- `cd frontend && npm run build`
- 部署后在各层级配置提示词，观察日志 `[wecom-bot] LLM POST ... messages` 首条是否为对应 system 消息。
