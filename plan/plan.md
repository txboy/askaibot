# askai — 开发方案

自托管聊天机器人，使用 **Vue 3 + FastAPI** 构建，暖色调主题。

自托管、可接入任意 OpenAI 兼容接口、支持企业微信登录与多会话管理、流式响应、Markdown/代码高亮、文件上传，并内置带左侧导航栏的管理后台。

---

## 1. 目标

- 简洁的聊天式界面（左侧会话侧边栏 + 主聊天区）
- 暖色主题（奶油底 `#fbf6ef` / 暖橙 `#e0804a` 点缀）
- 支持 OpenAI 兼容接口（自定义 `base_url` + `api_key` + 模型列表）
- 支持企业微信登录（网页授权 OAuth + 扫码）与手机号 + 验证码登录
- 多会话管理与历史持久化（SQLite）
- 流式（SSE 打字机）响应，支持 Markdown / 代码高亮
- 文件上传并发送给模型（图片走多模态，文本类提取文本）
- 管理后台：多接口管理、企微配置、Logo 定制、用户管理、统计、改密

---

## 2. 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite SPA |
| 后端 | FastAPI (Python) |
| 存储 | SQLite |
| 认证 | JWT |
| 流式 | SSE (Server-Sent Events) |
| 部署 | Docker Compose（nginx + uvicorn） |

---

## 3. 架构

- 前端：Vue 3 SPA，（左侧会话侧边栏 + 主聊天区），管理后台独立页面 `/admin`。
- 后端：FastAPI 本地运行，代理请求到任意 OpenAI 兼容接口，处理 SSE 流式，落库用户消息与助手消息（含 token 统计）。
- 存储：SQLite 保存用户 / 会话 / 消息 / 附件 / 设置 / 管理员 / LLM 接口。

---

## 4. 数据模型

### User（users）
| 字段 | 说明 |
|------|------|
| id | 主键 |
| nickname | 昵称 |
| avatar | 头像 |
| phone | 手机号 |
| wecom_userid | 企业微信 userid（可空） |
| created_at | 创建时间 |

### Conversation（conversations）
| 字段 | 说明 |
|------|------|
| id | 主键 |
| user_id | 所属用户 |
| title | 标题 |
| model | 使用的模型 |
| created_at / updated_at | 时间 |

### Message（messages）
| 字段 | 说明 |
|------|------|
| id | 主键 |
| conversation_id | 所属会话 |
| role | user / assistant / system |
| content | 内容 |
| **tokens** | 该次生成的 `usage.total_tokens`（用于 Token 统计） |
| created_at | 时间 |

### Setting（settings，全局共享一份，id=1）
| 字段 | 说明 |
|------|------|
| wecom_corp_id | 企业微信 CorpID |
| wecom_secret | 企业微信 Secret |
| wecom_agent_id | 企业微信应用 AgentId |
| wecom_redirect | 企业微信回调域名 |
| **logo_path** | 自定义 Logo 文件名（存于 upload_dir，空则用默认 Logo） |

### Attachment（attachments）
| 字段 | 说明 |
|------|------|
| id | 主键 |
| user_id / conversation_id / message_id | 归属 |
| filename / stored_name | 原始名 / 存储名 |
| content_type | MIME |
| kind | image / text / doc |
| extracted_text | 提取的文本 |
| size | 大小 |
| created_at | 时间 |

### Admin（admins）
| 字段 | 说明 |
|------|------|
| id | 主键 |
| username | 用户名 |
| password_hash | 密码哈希（PBKDF2） |

### ApiEndpoint（api_endpoints）
| 字段 | 说明 |
|------|------|
| id | 主键 |
| name | 接口名称 |
| base_url | OpenAI 兼容地址 |
| api_key | 密钥（服务端存储） |
| models | 逗号/换行分隔的模型列表 |
| enabled | 启用（1/0） |
| is_default | 默认接口（1/0） |
| created_at / updated_at | 时间 |

---

## 5. API 端点

### 认证
- `POST /api/auth/sms/send` — 发送本地模拟验证码
- `POST /api/auth/sms/verify` — 手机号 + 验证码登录
- `GET /api/auth/wecom/qrcode` — 获取企业微信扫码/授权信息
- `GET /api/auth/wecom/oauth` — 跳转企业微信网页授权
- `GET /api/auth/wecom/callback` — 处理授权回调换用户信息
- `GET /api/auth/me` — 当前用户信息

### 会话与消息（JWT 保护）
- `GET /api/conversations` — 会话列表
- `POST /api/conversations` — 新建会话
- `PUT /api/conversations/{id}` — 重命名
- `DELETE /api/conversations/{id}` — 删除
- `GET /api/conversations/{id}/messages` — 消息列表（含附件）

### 聊天
- `POST /api/chat` — SSE 流式，根据 `endpoint_id` / `model` 向对应接口发请求，落库用户与助手消息，并采集 `usage.total_tokens`。
- `POST /api/upload` — 上传文件（multipart），自动识别图片/文本/PDF/Word/Excel 并提取文本。
- `GET /api/files/{id}` — 读取上传文件（需认证），用于前端渲染图片缩略图。

### 用户侧接口
- `GET /api/endpoints` — 用户获取可用接口及模型列表（已启用，api_key 脱敏，不返回明文）。

### 管理后台（需管理员 JWT）
- `POST /api/admin/login` — 管理员登录（初始 `admin` / `admin123`）
- `GET/POST /api/admin/endpoints`、`PUT/DELETE /api/admin/endpoints/{id}` — 增删改 LLM 接口
- `GET/PUT /api/admin/wecom` — 企业微信登录配置
- `GET /api/admin/stats` — 首页统计（用户/会话/消息/接口/附件总数）
- `GET /api/admin/users` — 用户列表（含会话数、总 Token、当天 Token、最近活跃）
- `DELETE /api/admin/users/{id}` — 删除用户（级联删除其会话、消息、附件及磁盘文件）
- `GET/POST/DELETE /api/admin/logo` — Logo 状态 / 上传 / 恢复默认
- `PUT /api/admin/password` — 修改管理员密码（需验证旧密码）

### Logo（公开）
- `GET /api/logo` — 获取自定义 Logo（未设置返回 404，前端回退默认 Logo）

> 说明：`routers/brand.py` 为历史遗留，当前未在 `main.py` 注册，Logo 功能以 `admin.py` / `uploads.py` 中的实现为准。

---

## 6. 前端功能

### 登录页（`/login`）
- 三种登录入口：企业微信网页授权 / 扫码 / 手机号 + 验证码
- 品牌区 Logo：默认内置 Logo；后台上传自定义 Logo 后自动展示

### 聊天页（`/`）
- 侧边栏：Logo、新建会话、会话列表（删除/重命名）、用户栏
- 聊天区：流式打字机、Markdown 渲染、代码高亮 + 复制按钮
- 接口 / 模型下拉选择器
- 📎 文件上传按钮（图片 / 文本 / PDF / Word / Excel）

### 管理后台（`/admin`，左侧导航）
| 页 | 内容 |
|----|------|
| 首页 | 统计卡片（用户/会话/消息/接口/附件）+ 接口启用状态概览 |
| 用户列表 | 昵称、手机号、会话数、总 Token、当天 Token、注册/最近活跃时间、删除 |
| 接口设置 | 接口表格 + 添加/编辑/删除弹窗 |
| 企微设置 | CorpID / Secret / AgentId / 回调域名 |
| Logo设置 | 预览、选择图片、上传、恢复默认 |
| 修改密码 | 当前密码 + 新密码 + 确认（需验证旧密码） |

- 暖色主题：奶油底色、暖橙点缀。

---

## 7. 认证流程

1. 用户通过手机号验证码或企业微信登录
2. 后端校验后签发 JWT（普通用户 / 管理员两种）
3. 前端存储 token，后续请求带 `Authorization: Bearer <token>`
4. 受保护接口依赖当前用户 / 管理员

### 手机号 + 验证码（本地模拟）
- 发送验证码：后端生成 6 位验证码，本地返回（`SMS_MOCK=true`）
- 验证：校验验证码，创建/登录用户，签发 JWT

### 企业微信网页授权 / 扫码
- OAuth：重定向到企业微信授权页，回调携带 code
- 后端用 code 换 access_token，再获取用户信息（userid）
- 通过配置的 CorpID / Secret 实现；未配置时为本地模拟模式
- 扫码登录：通过生成授权二维码（企业微信扫码或授权链接二维码）

---

## 8. 目录结构

```
askai/
├─ plan/
│  └─ plan.md                    # 本文
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 # 入口、路由注册、启动迁移（新增列）、种子管理员
│  │  ├─ config.py               # pydantic-settings 配置
│  │  ├─ database.py             # SQLite 引擎 / Session
│  │  ├─ models.py               # 数据模型
│  │  ├─ schemas.py              # Pydantic 模型
│  │  ├─ auth.py                 # JWT 签发与校验（用户/管理员）
│  │  ├─ security.py             # PBKDF2 密码哈希
│  │  ├─ common.py               # get_setting / mask_key / parse_models
│  │  ├─ filetools.py            # 文件类型识别与文本提取
│  │  └─ routers/
│  │     ├─ auth.py              # 认证
│  │     ├─ conversations.py     # 会话与消息
│  │     ├─ chat.py              # SSE 流式 + token 统计
│  │     ├─ uploads.py           # 上传 / 公开 Logo
│  │     ├─ endpoints.py         # 用户侧接口列表
│  │     └─ admin.py             # 管理后台
│  ├─ requirements.txt
│  └─ app.db                     # SQLite（自动生成）
├─ frontend/
│  ├─ src/
│  │  ├─ main.js / App.vue
│  │  ├─ api.js                  # API 客户端
│  │  ├─ store.js                # 全局状态
│  │  ├─ style.css               # 全局暖色主题
│  │  ├─ router/index.js         # 路由（/、/login、/admin）
│  │  ├─ components/             # Logo / MarkdownContent / AttachmentImage
│  │  ├─ views/                  # Login / Chat / Admin
│  │  └─ utils/markdown.js
│  ├─ public/fonts/              # ZiHunBianTaoTi-2 字体
│  ├─ package.json / vite.config.js
├─ docker/
│  ├─ Dockerfile.backend
│  ├─ Dockerfile.frontend
│  ├─ nginx.conf
│  └─ docker-compose.yml
└─ source/logo/                  # Logo 源文件
```

---

## 9. 里程碑

1. ✅ 后端基础：数据库、模型、JWT 认证、会话/消息路由
2. ✅ 聊天接口：`/api/chat` SSE 流式 + token 统计
3. ✅ 认证登录：短信验证码（本地模拟）、企业微信 OAuth/扫码（可配置 + 模拟）
4. ✅ 文件上传：图片 / 文本 / PDF / Word / Excel 提取并发送
5. ✅ 前端：登录页、聊天界面（会话管理、Markdown、流式、暖色主题、上传）
6. ✅ 管理后台：多接口管理、企微配置、Logo 定制、用户列表 + Token 统计、统计、改密
7. ✅ Docker 部署与联调验证

---

## 10. 注意事项

- API Key 服务端存储，不返回明文给前端（接口列表做脱敏）。
- 企业微信需真实 CorpID / Secret 才能真实接入，提供本地模拟模式。
- 短信为本地模拟验证码，后续可替换为真实服务商（阿里云 / 腾讯云）。
- 数据库升级：`main.py` 启动时 `_ensure_columns()` 自动为 `settings` 补 `logo_path`、为 `messages` 补 `tokens` 列。
- 启动迁移与种子管理员在应用导入时执行，`--reload` 下会自动生效。

---

## 11. 运行方式

### 开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload

# 前端
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:5173

- 管理员在 `/admin` 管理后台配置 LLM 接口（初始 `admin` / `admin123`，建议尽快修改密码）
- 普通用户登录后在聊天框「接口/模型」下拉框选择接口与模型
- 登录方式：手机号 + 验证码（模拟）、企业微信（模拟 / 真实）
- 前端通过 Vite 代理将 `/api` 转发到后端 8000 端口

### Docker 一键启动

```bash
cd docker
docker compose up -d --build
```

- 后端：http://localhost:8000
- 前端：http://localhost（nginx 托管，`/api` 反向代理到 backend，已关闭缓冲以支持流式）
- 数据持久化于 Docker 卷 `app_data`（SQLite 位于 `/app/data/app.db`，附件位于 `/app/data/uploads`）
- 可选环境变量：`JWT_SECRET`（至少 32 字节）

### 环境变量（`backend/.env`，可选）

| 变量 | 说明 | 默认 |
|------|------|------|
| `JWT_SECRET` | JWT 密钥（至少 32 字节） | 内置占位 |
| `FRONTEND_URL` | 前端地址，用于企微回调跳转 | `http://localhost:5173` |
| `SMS_MOCK` | 是否使用模拟短信 | `true` |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./app.db` |
| `UPLOAD_DIR` | 上传目录 | `./data/uploads` |
| `MAX_UPLOAD_SIZE` | 上传上限（字节） | `20971520` |

---

## 12. 已完成状态

- [x] 后端：数据库模型、JWT 认证、会话/消息路由
- [x] 后端：`/api/chat` SSE 流式（OpenAI 兼容）+ `stream_options.include_usage` token 统计
- [x] 认证：手机号 + 验证码（本地模拟）、企业微信 OAuth/扫码（可配置 + 模拟）
- [x] 文件上传与发送（图片 `image_url`，文本/PDF/Word/Excel 提取文本）
- [x] 前端：登录页（三合一登录 + Logo）、聊天界面（会话、Markdown、代码高亮、流式、上传）
- [x] 管理后台（左侧导航）：首页统计、用户列表（含 Token）、接口设置、企微设置、Logo 设置、修改密码
- [x] Logo 定制：后台上传/恢复默认，登录页与侧边栏自动生效
- [x] Docker：nginx + uvicorn + 数据卷
- [x] 联调验证通过（后端 TestClient + 运行态端到端测试）
