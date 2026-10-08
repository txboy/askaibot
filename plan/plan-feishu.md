# 飞书兼容方案（机器人 + 授权登录）

> 目标：复用现有「企微/钉钉」架构，按 `provider` 分派，让系统同时支持**飞书机器人**（收发消息、LLM 回复）与**飞书授权登录**（扫码 OAuth + 飞书内免登）。
> 采用 **HTTP 回调（Webhook）** 模式，与现有企微/钉钉一致。

## 背景：现有多 provider 架构（可直接复用）

- **机器人**：`WecomBot` 已含 `provider` 列（`wecom`/`dingtalk`），`routers/*_bot.py` HTTP 回调；`wecom_bot.generate_reply()` 平台无关（LLM + MCP/技能/知识库工具）。
- **登录**：`auth.py` 的 `wecom_*`/`dingtalk_*` 四件套（qrcode/oauth/callback/free-login），用 userid 绑定 User 并 `create_token`。
- **数据**：`Setting`（wecom_*/dingtalk_*）、`User.wecom_userid/dingtalk_userid`、`main.py._ensure_columns()` 自动迁移。

飞书的**加解密/AES 方案与企微、钉钉不同**（飞书用 `sha256(EncryptKey)` 做 AES 密钥、标准 PKCS7），需新增独立的 `feishu_crypto.py`，其余逻辑可复用。

## 飞书 API 要点（已核对文档）

- **tenant_access_token**：`POST /open-apis/auth/v3/tenant_access_token/internal`，体 `{app_id, app_secret}` → `{code, tenant_access_token, expire}`
- **发消息**：`POST /open-apis/im/v1/messages?receive_id_type=open_id`，头 `Authorization: Bearer <token>`，体 `{receive_id, msg_type:"text", content:"{\"text\":\"...\"}"}`（content 为 JSON 字符串）
- **事件订阅（Webhook）**：开发者后台「事件订阅」填请求地址，订阅 `im.message.receive_v1`
  - **URL 验证**：飞书 `POST` 发送 `{"challenge":"...","token":"<校验Token>","type":"url_verification"}`，回应 `{"challenge":"..."}`；若启用加密，请求/响应均包在 `{"encrypt":"..."}` 中（需加解密）
  - **消息事件**（v2.0 `P2ImMessageReceiveV1`）：`header.event_type` + `event.sender.sender_id.{open_id,union_id,user_id}` + `event.message.{chat_id,chat_type,message_type,content}`；`content` 是 `{"text":"..."}` 字符串
- **登录 OAuth**：
  - 授权跳转：`https://open.feishu.cn/open-apis/authen/v1/authorize?app_id=<>&redirect_uri=<>&state=<>`
  - 换 token：`POST /open-apis/authen/v1/access_token`，体 `{grant_type:"authorization_code", app_id, app_secret, code}` → `{code, access_token, open_id, union_id, name, avatar_url}`
  - 免登：飞书客户端内用 `h5.getAuthCode()` / `tt.requestAuthCode()` 拿 `code`，再走上述换 token 接口

---

## A. 飞书机器人（消息收发）

### A1. 数据模型（复用 `WecomBot`，`provider='feishu'`）
- `WecomBot` 无需加列（`provider` 已有）。字段映射：`corp_id`=飞书 AppID、`secret`=AppSecret、`token`=校验 Token（选填）、`aes_key`=Encrypt Key（选填，用于事件解密）、`agent_id`=留空（飞书发送不需要）
- `User` 加 `feishu_userid`（unique，存 `union_id`，缺则 `open_id`）；`main.py._ensure_columns()` 加迁移

### A2. 新加解密模块 `feishu_crypto.py`
- `decrypt(encrypt_key, encrypt_str)` / `encrypt(encrypt_key, plaintext)`：AES-256-CBC，`key=sha256(encrypt_key).digest()`，`iv=key[:16]`，PKCS7（16 字节块）
- 不依赖 `wecom_crypto`（飞书与企微/钉钉加密不同）

### A3. 新核心模块 `feishu_bot.py`（仿 `dingtalk_bot.py`）
- `get_access_token(app_id, app_secret)`：POST 上述接口，内存缓存
- `send_text(open_id, content, app_id, app_secret)`：POST `/im/v1/messages?receive_id_type=open_id`，`content=json.dumps({"text": content})`
- 复用 `wecom_bot.generate_reply`（平台无关）

### A4. 新路由 `routers/feishu_bot.py`
- `POST /api/feishu/bot/{id}/callback`（飞书验证与事件均为 POST）
  - 读 JSON body；若含 `type=="url_verification"` 且**未加密**：校验 `token` 后返回 `{"challenge": ...}`
  - 若含 `encrypt`：用 `bot.aes_key` 解密出内层 JSON；内层若是 url_verification，返回 `{"encrypt": 重加密的 challenge JSON}`
  - 否则为消息事件：解析 `event` → `_handle`
- `_handle`：按 sender 的 `open_id`（或 `union_id`）建/取 User 与会话（`user_id`+`bot_id`）；`message_type=="text"` 时取 `content.text` 入库 → `generate_reply` → `send_text` 回复发起人；其他类型回复「暂不支持」
- `main.py` 注册该路由

### A5. 管理接口（`admin.py` + `schemas.py`）
- `_bot_callback_url` 增加 `provider=="feishu"` → `/api/feishu/bot/{id}/callback`
- `list_wecom_bots(provider='feishu')` 已支持（前端传入 `feishu` 即可）；`WecomBotCreate/Update/Out` 已含 `provider`

---

## B. 飞书授权登录

### B1. 全局设置（`Setting`）
`feishu_app_id`、`feishu_app_secret`、`feishu_redirect`（回调域名）

### B2. 用户
`User.feishu_userid`（unique），登录后绑定，`create_token` 签发会话

### B3. 共享核心（`auth.py`）
- `_feishu_user_token(app_id, app_secret, code)`：POST `/authen/v1/access_token`
- `_feishu_user_info(access_token)`：GET `/authen/v1/user_info`（若换 token 响应已含 name/avatar/open_id 可省略，实现时确认）

### B4. 接口（仿 `dingtalk_*`）
1. `GET /auth/feishu/qrcode`：有凭据返回真实授权链接，否则 debug 返回 mock，再否则 disabled
2. `GET /auth/feishu/oauth`：跳转飞书 OAuth2 授权页
3. `GET /auth/feishu/callback`：收 `code` → 换 user token → 取 `union_id` → 绑定/建 User → `create_token` 跳回 `/login?token=...`
4. `POST /auth/feishu/free-login`：前端在飞书内用 `h5.getAuthCode()` 拿 `code` POST 给后端；同法换 token 并返回 `TokenResponse`

`_feishu_is_real`：`app_id` 且 `app_secret` 已配置。

---

## C. 前端

- **登录页（Login.vue）**：加「飞书登录」tab；检测飞书 WebView（`window.h5`/`tt` 或 UA）走免登（`h5.getAuthCode`），否则展示扫码授权链接/二维码
- **后台（Admin.vue）**：新增导航「飞书设置」页
  - 「基础配置」卡片：AppID / AppSecret / 回调域名（供登录的全局凭据）
  - 「机器人」表格 + 弹窗：字段标签为 AppID/AppSecret/Token/EncryptKey（`provider='feishu'` 时），展示飞书回调地址；企微页只显示 `wecom`、钉钉页只显示 `dingtalk`、飞书页只显示 `feishu`
  - 机器人弹窗 label 增加 provider 分支（复用已做的 `botIsDingtalk` 模式）
- **api.js**：`getFeishu`、`feishuQrcode`、`feishuFreeLogin`、`adminGetFeishu`、`adminSaveFeishu`、`adminGetFeishuBots`

---

## D. 测试

- `test_feishu_crypto.py`：加解密 roundtrip（SHA-256 AES 方案）
- `test_feishu_bot.py`：URL 验证 challenge、消息事件→回复、`get_access_token`/`send_text`（mock httpx）、加密事件解密
- `test_feishu_login.py`：qrcode/oauth/callback/free-login（含 mock 模式）、`_feishu_user_token`
- 复用/更新现有测试；运行全量后端测试 + 前端 build

---

## 开放项（实现时确认）

- 飞书事件订阅 **URL 验证** 的精确请求/响应字段（`challenge`/`token`/是否需回传加密）——文档为 JS 渲染，需实现时按官方文档/实测核对
- 飞书**事件 v2.0（`header`/`event`）与 v1.0（`data`）结构**差异——用 `header.event_type` 判断并兼容
- 飞书**加密算法**（`sha256(EncryptKey)` 密钥 + `iv=key[:16]` + PKCS7）需实现时核对官方代码
- `/authen/v1/access_token` 是否已含 `name/avatar_url`（决定是否再调 `user_info`）
- 飞书内免登的 `h5.getAuthCode()` 在真实客户端的行为（前端探测方式）
