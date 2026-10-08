# 钉钉兼容方案（机器人 + 授权登录）

> 目标：让系统同时支持**钉钉机器人**（接收钉钉消息、LLM 回复）与**钉钉授权登录**（扫码 OAuth + 钉钉内免登）。
> 复用现有企微机器人与登录架构，按 `provider` 分派。

## 背景：现有企微架构

- **机器人**：`GET/POST /api/wecom/bot/{id}/callback`（`routers/wecom_bot.py`），用 `wecom_crypto.py`（AES-256-CBC + WXBizMsgCrypt）验签解密 XML；`bot_core.generate_reply()`（LLM + MCP/技能/知识库工具）→ `send_text()` 发送。
- **登录**：`auth.py` 的 `/auth/wecom/qrcode`、`/oauth`、`/callback`，用 `wecom_userid` 绑定用户并 `create_token`。
- **模型**：`WecomBot`（corp_id/secret/agent_id/token/aes_key/kb_ids/…）、`Setting`（wecom_*）、`User.wecom_userid`。

钉钉与企微在很多方面**相似**（加解密、文本消息 XML 结构），可直接复用；差异在验签参数名、密文包裹格式、取 token / 发送接口 / 用户接口。

## 钉钉 API 要点

- **access_token（发消息/取服务端 token）**：`GET /gettoken?appkey=&appsecret=` → `{access_token, expires_in, errcode}`
- **发消息**：`POST /topapi/message/corpconversation/asyncsend_v2?access_token=`，体 `{agent_id, userid_list, msg}`（`msg` 为 JSON 字符串）
- **用户登录 token**：`POST /v1.0/oauth2/userAccessToken`，体 `{clientId, clientSecret, code, grantType:"authorization_code"}` → `{accessToken, ...}`
- **用户信息**：`GET /v1.0/contact/users/me`，头 `x-acs-dingtalk-access-token:` → `{userId, nick, avatarUrl}`
- **扫码 OAuth 跳转**：`https://login.dingtalk.com/oauth2/auth?client_id=<AppKey>&response_type=code&scope=openid&prompt=consent&redirect_uri=<callback>&state=<state>`
- **回调加解密**：签名 `sha1(sort(token, timestamp, nonce, encrypt))`，AES 与企微相同（`wecom_crypto` 可复用）；receive_id 为钉钉 `corpId`

---

## A. 钉钉机器人（消息收发）

### 1. 数据模型
- `WecomBot` 加 `provider` 列（`VARCHAR DEFAULT 'wecom'`）——迁移见 `main.py._ensure_columns`
- `User` 加 `dingtalk_userid`（unique，存钉钉 userId）
- 字段复用映射（不新增列）：`corp_id`=钉钉 AppKey、`secret`=AppSecret、`agent_id`=AgentId、`token`=回调 Token、`aes_key`=EncodingAESKey（按 `provider` 解释语义）

### 2. 加解密（`wecom_crypto.py`）
- WXBizMsgCrypt 算法与钉钉相同，直接复用
- `decrypt_msg` 增加可选 `check_receive_id`；钉钉用 token 签名已验真，跳过 receive_id 校验（因钉钉 receive_id=corpId 未单独存）

### 3. 新核心模块 `dingtalk_bot.py`（仿 `wecom_bot.py`）
- `get_access_token(app_key, app_secret)`：`GET /gettoken?appkey=&appsecret=`，带内存缓存
- `send_text(userid, text, agent_id, app_key, app_secret)`：`POST /topapi/message/corpconversation/asyncsend_v2`
- 复用 `wecom_bot.generate_reply`（平台无关，LLM + 工具）

### 4. 新路由 `routers/dingtalk_bot.py`
- `GET /dingtalk/bot/{id}/callback`：URL 验证（验签 + 解密 `echostr` 并返回明文）
- `POST /dingtalk/bot/{id}/callback`：验签解密 → 解析消息 → `_handle`，返回 `success`
- `_handle`：按 `FromUserName`(`userId`) 建/取 `User`（`dingtalk_userid`）与会话（`user_id`+`bot_id`）；文本消息入库 → `generate_reply` → `send_text` 回复发起人；其他类型回复「暂不支持」
- `main.py` 注册该路由

### 5. 管理接口（`admin.py` + `schemas.py`）
- `WecomBotCreate/Update/Out` 加 `provider`
- `list_wecom_bots` 支持 `?provider=`（默认 `wecom`）
- `_bot_callback_url` 按 `provider` 返回 `/api/wecom/bot/{id}/callback` 或 `/api/dingtalk/bot/{id}/callback`

---

## B. 钉钉授权登录

### 1. 全局设置（`Setting`）
`dingtalk_app_key`、`dingtalk_app_secret`、`dingtalk_agent_id`、`dingtalk_redirect`（回调域名）

### 2. 用户
`User.dingtalk_userid`（unique），登录后绑定，`create_token` 签发会话

### 3. 共享核心（`auth.py`）
- `_dingtalk_user_token(app_key, app_secret, code)`：`POST /v1.0/oauth2/userAccessToken`
- `_dingtalk_user_info(access_token)`：`GET /v1.0/contact/users/me`

### 4. 接口（仿 `wecom_*`）
1. `GET /auth/dingtalk/qrcode`：有凭据返回真实登录链接，否则 debug 返回 mock，再否则 disabled
2. `GET /auth/dingtalk/oauth`：跳转钉钉 OAuth2 授权页
3. `GET /auth/dingtalk/callback`：收 `code` → 换 token → 取 `userId` → 绑定/建 `User` → `create_token` 跳回 `/login?token=...`
4. `POST /auth/dingtalk/free-login`（免登）：前端在钉钉内用 `dd.runtime.permission.requestAuthCode` 拿 `authCode`，POST 给后端；后端同法换 token+取用户，直接返回 `TokenResponse`（JSON）

`_dingtalk_is_real` 判定：`app_key` 且 `app_secret` 已配置。

---

## C. 前端

- **登录页**：加「钉钉登录」入口；检测钉钉 WebView 环境走免登（dd SDK），否则走扫码 OAuth 跳转
- **独立导航项「钉钉机器人」**：复用机器人表格/弹窗，字段标签为 AppKey/AppSecret/AgentId/Token/AESKey，展示钉钉回调地址；企微页只显示 `provider='wecom'`，钉钉页只显示 `provider='dingtalk'`
- **系统设置**：加钉钉 AppKey/AppSecret/AgentId/回调域名（全局，供登录）
- `api.js`：`adminGetWecomBots(provider)`、机器人创建/更新带 `provider`

---

## D. 测试

- 复用 `wecom_crypto` 加解密单测
- 新增 `dingtalk_bot` 路由测试：URL 验证、收消息→回复、`get_access_token`/`send_text`（mock httpx）
- 新增钉钉登录测试：`qrcode`/`oauth`/`callback`/`free-login`（含 mock 模式）、`_dingtalk_user_token`/`_dingtalk_user_info`
- 更新 `test_wecom_bot` 适配 `provider` 字段

---

## 开放项（实现时确认）

- 钉钉 HTTP 回调的**密文包裹格式**（`{"encrypt":...}` JSON vs XML）与**明文消息格式**（XML vs JSON）——钉钉文档为 JS 渲染未能直接抓取，需查文档/实测
- `/v1.0/oauth2/userAccessToken` 与 `/v1.0/contact/users/me` 的精确字段与返回结构
- 钉钉机器人 v1 仅支持**文本**消息，图片/多媒体下载留作后续
