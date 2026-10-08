# 架构总览

askaibot 是一个自托管聊天机器人，前后端分离：前端 Vue 3 SPA，后端 FastAPI，默认 SQLite 存储，SSE 流式对话，Docker Compose 一键部署。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3（`<script setup>` SFC）+ Vite + Vue Router 4，手写响应式 store，markdown-it + highlight.js，FontAwesome |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 存储 | SQLite（默认），可热切换 MySQL / PostgreSQL / MSSQL / Oracle |
| 认证 | JWT（用户与管理员两套独立 Token） |
| 流式 | SSE（Server-Sent Events） |
| 模型接口 | 任意 OpenAI 兼容 `/chat/completions` |
| 部署 | Docker Compose（nginx + uvicorn） |

## 目录结构

```
askaibot/
├─ backend/                        # FastAPI 后端
│  ├─ app/
│  │  ├─ main.py                   # 入口：启动建表/补列、注册路由、播种管理员
│  │  ├─ config.py                 # pydantic-settings 配置（.env 可覆盖）
│  │  ├─ database.py               # 引擎/会话管理、数据库配置解析、热切换
│  │  ├─ auth.py                   # JWT 签发校验、用户/管理员依赖注入
│  │  ├─ security.py               # PBKDF2 密码哈希
│  │  ├─ schemas.py                # Pydantic 请求/响应模型
│  │  ├─ filetools.py              # 文件类型识别与文本提取
│  │  ├─ models/                   # SQLAlchemy 模型（19 个表）
│  │  ├─ controllers/
│  │  │  ├─ frontend/              # 用户侧接口
│  │  │  ├─ admin/                 # 管理后台接口（18 个模块）
│  │  │  └─ webhook/               # 企微/钉钉/飞书机器人回调
│  │  └─ services/                 # 业务服务（SMS、验证码、KB、MCP、技能、搜索、配额、审计、DB 迁移、各平台机器人）
│  ├─ reset_admin_secret.py        # 运维脚本：清除后台随机地址
│  ├─ requirements.txt
│  └─ data/                        # 运行时数据（app.db、uploads、db_config.json、backups）
├─ frontend/                       # Vue 3 前端
│  ├─ src/
│  │  ├─ main.js / App.vue
│  │  ├─ api.js                    # API 客户端 + SSE 解析
│  │  ├─ store.js                  # 全局状态（token / admin / user）
│  │  ├─ theme.js                  # 主题切换
│  │  ├─ style.css                 # 主题变量与全局样式
│  │  ├─ router/index.js           # 路由与导航守卫
│  │  ├─ composables/              # useChat / useConfirm
│  │  ├─ components/               # 通用组件 + chat/ + admin/
│  │  ├─ views/                    # Login / Chat / Admin / NotFound + admin 子页面
│  │  └─ utils/markdown.js
│  ├─ public/fonts/                # ZiHunBianTaoTi-2 字体
│  └─ package.json / vite.config.js
├─ docker/                         # Dockerfile.backend / Dockerfile.frontend / nginx.conf / docker-compose.yml
├─ plan/                           # 开发方案文档
└─ docs/                           # 本技术文档目录
```

## 运行时拓扑

```
浏览器 ──HTTP──> nginx (frontend, :80)
                   ├─ /             → 静态 SPA
                   └─ /api/         → backend:8000 (proxy_buffering off，支持 SSE)
                                        │
                                        ├─ SQLite / MySQL / PostgreSQL / MSSQL / Oracle
                                        ├─ 上传目录 /app/data/uploads
                                        └─ 外部 OpenAI 兼容模型接口
```

开发模式下 Vite Dev Server（5173）把 `/api` 代理到 `http://localhost:8000`。

## 请求鉴权模型

- **用户**：`Authorization: Bearer <user JWT>`，payload `{sub: user_id, exp}`。
- **管理员**：独立 Token，payload `{sub: username, role, department_id, exp}`；`role ∈ {super, dept}`。
- 用户与管理员会话完全独立，前端分别存放在 `localStorage['token']` 与 `localStorage['admin_token']`。

## 相关文档

- [后端实现](backend.md)
- [前端实现](frontend.md)
- [功能详解](features.md)
- [数据模型](data-model.md)
- [API 参考](api.md)
- [部署与运维](deployment.md)
