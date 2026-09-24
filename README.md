# askai — 自托管聊天机器人

一个自托管聊天机器人，使用 **Vue 3 + FastAPI** 构建，采用暖色调主题（奶油底 / 暖橙点缀）。

支持接入任意 **OpenAI 兼容接口**，提供手机号验证码与企业微信登录、多会话管理、流式（打字机）响应、Markdown 渲染与代码高亮、文件上传发送给模型，并内置一个带导航栏的管理后台。

---

## ✨ 功能特性

- **暖色主题**：奶油底色 + 暖橙 (`#e0804a`) 点缀
- **多会话管理**：新建 / 删除 / 重命名会话，历史消息持久化到 SQLite
- **流式响应**：SSE（Server-Sent Events）打字机效果，支持中途取消
- **Markdown 与代码高亮**：`markdown-it` + `highlight.js`，代码块带一键复制
- **多 LLM 接口管理**：管理员可维护多个 OpenAI 兼容接口（`base_url` / `api_key` / 模型列表），用户在前端选择接口与模型
- **文件上传**：图片以 `image_url`（base64）发送；文本 / PDF / Word / Excel 自动提取文本后嵌入消息
- **三种登录方式**：手机号 + 验证码（本地模拟）、企业微信网页授权（OAuth）、企业微信扫码
- **管理后台**（左侧导航）：首页统计、用户列表、接口设置、企微设置、Logo 设置、系统设置、修改密码
  - 首页：注册用户 / 会话 / 消息 / 接口 / 附件总数 + 接口启用状态概览
  - 用户列表：昵称、手机号、会话数、**总 Token**、**当天 Token**、注册/最近活跃时间，支持删除用户（级联删除其会话、消息与附件）
  - Logo 设置：上传自定义 Logo（登录页与侧边栏自动生效），可恢复默认
  - 系统设置：主题、调试模式、站点标题、Favicon，以及**后台随机地址**（开启后仅能用 `?r=随机参数` 访问后台，否则 404）
- **Token 统计**：聊天时采集模型返回的 `usage.total_tokens`，按用户汇总展示

---

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite SPA |
| 后端 | FastAPI (Python) |
| 存储 | SQLite |
| 认证 | JWT |
| 流式 | SSE (Server-Sent Events) |
| 部署 | Docker Compose（nginx + uvicorn） |

---

## 📁 目录结构

```
askai/
├─ backend/                        # FastAPI 后端
│  ├─ app/
│  │  ├─ main.py                   # 应用入口、路由注册、启动迁移
│  │  ├─ config.py                 # 配置（env 可覆盖）
│  │  ├─ database.py               # SQLite / SQLAlchemy 引擎
│  │  ├─ models.py                 # 数据模型
│  │  ├─ schemas.py                # Pydantic 模型
│  │  ├─ auth.py                   # JWT 签发与校验
│  │  ├─ security.py               # 密码哈希
│  │  ├─ common.py                 # 共享工具（设置、脱敏、模型解析）
│  │  ├─ filetools.py              # 文件类型识别与文本提取
│  │  └─ routers/
│  │     ├─ auth.py                # 登录 / 企业微信 / 短信
│  │     ├─ conversations.py       # 会话与消息
│  │     ├─ chat.py                # SSE 流式聊天
│  │     ├─ uploads.py             # 文件上传 / Logo
│  │     ├─ endpoints.py           # 用户侧接口列表
│  │     └─ admin.py               # 管理后台
│  ├─ reset_admin_secret.py        # 命令行工具：清除后台随机地址设置
│  ├─ requirements.txt
│  └─ app.db                       # SQLite 数据库（自动生成）
├─ frontend/                       # Vue 3 前端
│  ├─ src/
│  │  ├─ main.js / App.vue
│  │  ├─ api.js                    # API 客户端
│  │  ├─ store.js                  # 全局状态（token / user）
│  │  ├─ style.css                 # 全局暖色主题
│  │  ├─ router/index.js           # 路由（/、/login、/admin）
│  │  ├─ components/               # Logo / Markdown / 附件图片等
│  │  ├─ views/                    # Login / Chat / Admin
│  │  └─ utils/markdown.js
│  ├─ public/fonts/                # ZiHunBianTaoTi-2 字体
│  ├─ package.json / vite.config.js
├─ docker/                         # Docker 部署配置
│  ├─ Dockerfile.backend
│  ├─ Dockerfile.frontend
│  ├─ nginx.conf
│  └─ docker-compose.yml
├─ source/logo/                    # Logo 源文件
└─ plan/plan.md                    # 开发方案
```

---

## 🚀 快速开始

### 1. 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 **http://localhost:5173**（Vite 已将 `/api` 代理到后端 8000 端口）。

### 3. 管理后台

访问 **http://localhost:5173/admin**

- 初始管理员账号：**admin** / **admin123**
- 首次登录后请及时在「修改密码」中更换密码

---

## 🐳 Docker 一键部署

```bash
cd docker
docker compose up -d --build
```

- 前端：http://localhost（nginx 托管，`/api` 反向代理至 backend，已关闭缓冲以支持流式）
- 后端：http://localhost:8000
- 数据持久化于 Docker 卷 `app_data`（SQLite 位于 `/app/data/app.db`，上传附件位于 `/app/data/uploads`）

---

## ⚙️ 环境变量（可选）

在 `backend/` 下创建 `.env` 文件（或通过 Docker 时的 `environment` 传入）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET` | JWT 密钥（至少 32 字节） | 内置占位符 |
| `FRONTEND_URL` | 前端地址（用于企微回调跳转） | `http://localhost:5173` |
| `SMS_MOCK` | 是否使用本地模拟短信验证码 | `true` |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./app.db` |
| `UPLOAD_DIR` | 上传文件目录 | `./data/uploads` |
| `MAX_UPLOAD_SIZE` | 上传大小上限（字节） | `20971520`（20MB） |

---

## 🛠 运维命令

### 清除后台随机地址（重置后台入口）

后台系统设置中的「**后台随机地址**」开启后，只有携带正确 `?r=随机参数` 才能进入后台（否则显示 404）。若**忘记随机参数导致无法登录后台**，可在服务器上运行以下命令一键重置：关闭随机后台地址开关并清空随机参数，之后可直接通过 `/admin` 进入。

```bash
cd backend
python reset_admin_secret.py
```

执行成功输出示例：

```
[OK] 已清除后台随机地址设置
   admin_secret_enabled = 0
   admin_secret         = ''
现在可直接访问 /admin 进入后台。
```

说明：

- 脚本读取环境变量 `DATABASE_URL`（默认 `sqlite:///./app.db`），与应用共用同一数据库。
- 重置后请在后台「系统设置 → 后台随机地址」中重新生成随机参数（如需再次启用）。

### Docker 部署下清除后台随机地址

Docker 部署时，`reset_admin_secret.py` 已随镜像拷贝进后端容器 `/app`，且容器内 `DATABASE_URL=sqlite:////app/data/app.db`（存于 `app_data` 卷），无需额外传参，直接在宿主机执行：

```bash
# 按容器名
docker exec -it chatbot-backend python reset_admin_secret.py

# 或按服务名
docker compose exec backend python reset_admin_secret.py
```

- 容器名 `chatbot-backend`，服务名 `backend`（见 `docker/docker-compose.yml`）
- 数据持久化于 `app_data` 卷（容器内 `/app/data`）；若卷被清空，随机地址设置也会一并丢失

---

## 🔌 API 概览

所有用户接口使用 `Authorization: Bearer <token>`；管理接口使用管理员 JWT。

**认证**
- `POST /api/auth/sms/send` — 发送本地模拟验证码
- `POST /api/auth/sms/verify` — 手机号 + 验证码登录
- `GET /api/auth/wecom/qrcode` — 获取企业微信扫码/授权信息
- `GET /api/auth/wecom/oauth` — 企业微信网页授权跳转
- `GET /api/auth/wecom/callback` — 处理授权回调
- `GET /api/auth/me` — 当前用户信息

**会话与消息**
- `GET /api/conversations` / `POST /api/conversations` — 列表 / 新建
- `PUT /api/conversations/{id}` — 重命名
- `DELETE /api/conversations/{id}` — 删除
- `GET /api/conversations/{id}/messages` — 消息列表

**聊天**
- `POST /api/chat` — SSE 流式聊天（请求体包含 `conversation_id`、`content`、可选 `endpoint_id`、`model`、`attachment_ids`）
- `POST /api/upload` — 上传文件（multipart）
- `GET /api/files/{id}` — 读取上传文件（用于图片缩略图）

**用户侧接口**
- `GET /api/endpoints` — 可用的 LLM 接口与模型列表

**管理后台**
- `POST /api/admin/login` — 管理员登录
- `GET/POST /api/admin/endpoints`、`PUT/DELETE /api/admin/endpoints/{id}` — 接口增删改
- `GET/PUT /api/admin/wecom` — 企业微信登录配置
- `GET/POST/DELETE /api/admin/logo` — Logo 状态 / 上传 / 恢复默认
- `GET /api/admin/stats` — 首页统计
- `GET/DELETE /api/admin/users` — 用户列表 / 删除用户（含 Token 统计）
- `PUT /api/admin/password` — 修改管理员密码（需验证旧密码）

**Logo**
- `GET /api/logo` — 获取当前自定义 Logo（未设置时 404）

---

## 🗄 数据模型（SQLite）

| 表 | 关键字段 |
|----|----------|
| `users` | id, nickname, phone, wecom_userid, created_at |
| `conversations` | id, user_id, title, model, created_at, updated_at |
| `messages` | id, conversation_id, role, content, **tokens**, created_at |
| `settings` | 全局设置（微信参数 + logo_path） |
| `attachments` | id, user_id, conversation_id, message_id, filename, stored_name, content_type, kind, extracted_text, size |
| `admins` | id, username, password_hash |
| `api_endpoints` | id, name, base_url, api_key, models, enabled, is_default |

---

## 🔑 登录机制说明

- **手机号 + 验证码**：本地模拟模式（`SMS_MOCK=true`），后端生成 6 位验证码并返回 / 打印，用于开发联调；可替换为真实短信服务商。
- **企业微信**：需配置 CorpID / Secret / AgentId / 回调域名后启用；未配置时自动使用模拟模式，方便本地演示。
- **Token 统计**：聊天时后端向模型请求 `stream_options.include_usage`，将返回的 `total_tokens` 记入对应助手消息，管理后台据此汇总生成各用户的总 Token 与当天 Token。

---

## 📝 备注

- API Key 仅存储在服务端，接口列表对前端做脱敏，不返回明文。
- 管理后台 `admin` / `admin123` 为初始账号，部署后务必修改。
- 计划文档见 [`plan/plan.md`](plan/plan.md)。
