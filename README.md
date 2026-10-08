# askai — 自托管聊天机器人

一个开源自托管聊天机器人，使用 **Vue 3 + FastAPI** 构建，接入任意 **OpenAI 兼容接口**。界面采用暖色主题（奶油底 / 暖橙点缀），开箱即用，数据完全掌握在自己手里。

## 它能做什么

- 💬 **多会话聊天**：新建 / 重命名 / 删除会话，历史持久化
- ⚡ **流式响应**：SSE 打字机效果，支持中途取消
- 📝 **Markdown 与代码高亮**：代码块一键复制
- 📎 **文件上传**：图片、文本、PDF、Word、Excel 直接发给模型
- 🔌 **多模型接口**：管理员维护多个 OpenAI 兼容接口，用户在聊天中选择
- 📚 **知识库**：接入 Dify / RAGFlow，支持用户选择或模型自主检索
- 🧰 **MCP 工具**与**技能包（Skill）**：让模型调用外部工具
- 🌐 **联网搜索**：Tavily / Bing / SearXNG / DuckDuckGo
- 🔑 **多种登录**：手机号验证码、企业微信、钉钉、飞书
- 🛡️ **三层权限**：超级管理员 / 部门管理员 / 普通用户，含部门、用户组与审计日志
- 🤖 **机器人接入**：企业微信、钉钉、飞书群机器人
- 🎨 **可定制**：Logo、Favicon、站点标题、助手形象、主题（暖 / 冷 / 暗）

## 快速开始

### Docker 一键部署（推荐）

```bash
cd docker
docker compose up -d --build
```

启动后：

- 聊天前台：http://localhost
- 管理后台：http://localhost/admin

### 本地开发

**后端**

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:5173 （Vite 已把 `/api` 代理到后端）。

## 首次使用

1. 打开后台 **http://localhost/admin**，使用初始账号登录：
   - 用户名：`admin`
   - 密码：`admin123`
   > ⚠️ 首次登录后请立即在「修改密码」中更换。
2. 在「工具接入 → 接口设置」新增一个 OpenAI 兼容接口（`base_url`、`api_key`、模型列表）。
3. 回到前台 http://localhost ，用手机号（开发默认模拟验证码）等方式登录，即可开始对话。

> 默认后端以模拟模式运行短信（`SMS_MOCK=true`），验证码会直接返回/打印，便于本地体验。生产环境请在管理后台配置真实短信服务商。

## 管理后台功能

左侧导航按角色显示。超级管理员可管理：

| 分组 | 功能 |
|------|------|
| 用户管理 | 用户列表、部门、管理员账号、用户组 |
| 工具接入 | 接口设置、短信接口、联网搜索、MCP 工具、技能包、知识库 |
| 渠道接入 | 企业微信、钉钉、飞书 |
| 系统管理 | 系统设置、数据库、审计日志、协议管理 |

其他能力：Token 用量统计与每日限额、首页数据概览、数据库在线备份与热切换、后台随机地址（`/admin?r=<随机参数>`）、协议强制同意等。

## 忘记后台入口？

若开启了「后台随机地址」又忘记 `?r=` 参数，在服务器上执行：

```bash
cd backend && python reset_admin_secret.py
```

Docker 部署下：

```bash
docker exec -it chatbot-backend python reset_admin_secret.py
```

## 配置

可选环境变量（在 `backend/.env` 或 Docker 环境变量中设置），常用项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET` | JWT 密钥（生产务必修改，≥32 字节） | 内置占位符 |
| `FRONTEND_URL` | 前端地址（OAuth 回调跳转） | `http://localhost:5173` |
| `SMS_MOCK` | 是否使用本地模拟短信验证码 | `true` |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./data/app.db` |
| `MAX_UPLOAD_SIZE` | 上传大小上限（字节） | `20971520`（20MB） |

完整列表见 [部署与运维](docs/deployment.md#环境变量)。

## 文档

- [架构总览](docs/architecture.md)
- [后端实现](docs/backend.md)
- [前端实现](docs/frontend.md)
- [功能详解](docs/features.md)
- [数据模型](docs/data-model.md)
- [API 参考](docs/api.md)
- [部署与运维](docs/deployment.md)

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite |
| 后端 | FastAPI + SQLAlchemy |
| 存储 | SQLite（可热切换 MySQL / PostgreSQL / MSSQL / Oracle） |
| 认证 | JWT |
| 流式 | SSE |
| 部署 | Docker Compose（nginx + uvicorn） |

## 备注

- API Key 仅存储在服务端，接口列表对前端脱敏，不返回明文。
- 数据库可在后台热切换，支持 SQLite / MySQL / PostgreSQL / MSSQL / Oracle。
- 开发方案见 [`plan/plan.md`](plan/plan.md)。
