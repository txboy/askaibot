# 部署与运维

## 本地开发

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 （Vite 已把 `/api` 代理到后端 8000）。后台入口 http://localhost:5173/admin ，初始账号 `admin` / `admin123`。

## Docker 部署

```bash
cd docker
docker compose up -d --build
```

- 前端：http://localhost （nginx 托管，`/api` 反向代理至 backend）
- 后端：http://localhost:8000

### docker-compose.yml

两个服务，使用**宿主机绑定挂载**（非命名卷）持久化数据：

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| `backend` | `chatbot-backend` | `8000:8000` | 挂载 `../backend/data:/app/data` |
| `frontend` | `chatbot-frontend` | `80:80` | 依赖 backend |

后端环境变量可用宿主机变量覆盖：`FRONTEND_URL`（默认 `http://localhost`）、`JWT_SECRET`。

### Dockerfile.backend

基于 `python:3.12-slim`，安装依赖并复制后端到 `/app`。镜像内置运行时环境变量：

- `DATABASE_URL=sqlite:////app/data/app.db`
- `UPLOAD_DIR=/app/data/uploads`
- `DB_CONFIG_FILE=/app/data/db_config.json`
- `FRONTEND_URL=http://localhost`
- `SKILL_TIMEOUT=60`

启动命令：`uvicorn app.main:app --host 0.0.0.0 --port 8000`。

> 注：镜像未安装 Docker CLI/SDK，技能在本地软沙箱中执行。

### Dockerfile.frontend

多阶段构建：`node:22-alpine` 执行 `npm ci && npm run build`，产物 `dist` 由 `nginx:alpine` 托管。

### nginx.conf

- `location /api/` → `http://backend:8000`（Docker 服务名）。
- 为支持 SSE 关闭缓冲并延长超时：`proxy_buffering off`、`proxy_cache off`、`proxy_read_timeout 3600s`、`proxy_send_timeout 3600s`、`proxy_http_version 1.1`。
- `location /` → `try_files $uri $uri/ /index.html`（SPA 回退）。

## GitHub Codespaces 预览（免服务器）

> ⚠️ 仅用于演示/预览，非生产环境。空闲会自动停止，受免费额度限制；数据随 codespace 删除而丢失。

1. 仓库页 **Code → Codespaces → Create codespace on master**。
2. 创建完成后（`.devcontainer` 会自动预构建镜像），在终端执行：

   ```bash
   cd docker && docker compose up -d
   ```

3. 打开 **Ports** 面板 → 端口 **80** → 右键 **Port Visibility → Public**。
4. 访问 `https://<codespace 名>-80.app.github.dev`；后台 `/admin`，账号 `admin/admin123`。

注意：每次**新建** codespace 都需重新把端口 80 设为 Public；同一 codespace 重启会保留端口可见性。

## 环境变量

`backend/.env`（从 `.env.example` 复制）或 Docker 环境变量。`config.py` 字段名大小写不敏感。

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET` | JWT 密钥（建议 ≥32 字节） | 内置占位符 |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token 有效期（分钟） | `10080`（7 天） |
| `FRONTEND_URL` | 前端地址（OAuth 回调跳转） | `http://localhost:5173` |
| `DEBUG` | 调试模式 | `False` |
| `SMS_MOCK` | 本地模拟短信验证码 | `True` |
| `UPLOAD_DIR` | 上传目录 | `./data/uploads` |
| `MAX_UPLOAD_SIZE` | 上传大小上限（字节） | `20971520`（20MB） |
| `DB_CONFIG_FILE` | 数据库配置 JSON 路径 | `./data/db_config.json` |
| `SKILL_TIMEOUT` | 技能执行超时（秒） | `60` |
| `DATABASE_URL` | 数据库连接串（被 `db_config.json` 覆盖） | `sqlite:///./data/app.db` |

数据库 URL 解析优先级：`db_config.json` > `DATABASE_URL` > 默认 SQLite。

## 数据库支持与热切换

支持 **SQLite**（内置）、**MySQL**（pymysql）、**PostgreSQL**（psycopg2）、**SQL Server**（pymssql）、**Oracle**（oracledb）。驱动均在 `requirements.txt` 中。

后台「系统管理 → 数据库」可在线切换：填写目标连接 → 测试 → 迁移并切换。切换流程：校验配置 → 测试连接 → 迁移（默认先备份 SQLite）→ 保存 `db_config.json` → 热切换引擎 → 重建 schema → 写审计日志。**附件文件不随迁移复制**。

Oracle 使用 `?service_name=<database>` 连接；对旧 schema 主键非 identity 的情况，启动时会自动修复并复位序列。

## 运维命令

### 清除后台随机地址

开启「后台随机地址」后，若遗忘 `?r=` 参数将无法进入后台。运行脚本重置：

```bash
cd backend
python reset_admin_secret.py
```

脚本读取 `DATABASE_URL`（默认 `sqlite:///./app.db`），将 `admin_secret_enabled` 置 0、清空 `admin_secret`，之后可直接访问 `/admin`。

Docker 下脚本已在镜像 `/app` 内，容器 `DATABASE_URL=sqlite:////app/data/app.db`，直接执行：

```bash
docker exec -it chatbot-backend python reset_admin_secret.py
# 或
docker compose exec backend python reset_admin_secret.py
```

### 数据库备份

后台「数据库」页可一键备份当前 SQLite 文件到 `data/backups/app_<时间戳>.db`。

## 数据持久化

Docker 部署数据位于宿主机 `backend/data/`（容器内 `/app/data`）：

- `app.db` — SQLite 数据库（若未切换）
- `uploads/` — 上传附件
- `db_config.json` — 数据库配置
- `backups/` — 备份

若清空该目录，随机后台地址等设置会一并丢失。
