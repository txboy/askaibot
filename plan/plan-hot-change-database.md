# askai — 数据库切换功能（热切换）

> 方案文档。目标：在管理后台新增「数据库」页，支持当前 SQLite 与 **MySQL / PostgreSQL / SQL Server / Oracle** 之间切换；切换时将现有数据完整迁移到目标库，并**免重启热切换**。

---

## 0. 已确认的决策

| 项 | 结论 |
|----|------|
| 切换生效方式 | **免重启热切换**（进程内替换 engine/SessionLocal，并持久化到配置文件） |
| SQL Server 驱动 | **pymssql**（纯 Python + FreeTDS，无需系统 ODBC 驱动） |
| String 长度规范化 | **同意**（14 个模型的无长度 `String` 列补长度，短字段 255 / 长字段改 Text） |

---

## 1. 现状与关键难点

1. **engine 在进程加载时锁定**：`backend/app/database.py` 用 `DATABASE_URL` 环境变量创建 engine；`main.py`、`controllers/webhook/feishu_bot.py`、`reset_admin_secret.py` 直接 `import SessionLocal` / `engine`。
2. **配置持久化冲突**：Docker 里 `DATABASE_URL` 由 Dockerfile `ENV` 写死，运行时写 `.env` 无法覆盖（环境变量优先级高于 `.env`）。因此 DB 配置**不能只放 `.env`**，必须放随 `app_data` 卷持久化的文件。
3. **Schema 不跨库**：`Base.metadata.create_all` + `main.py::_ensure_columns()`（`ALTER TABLE ... ADD COLUMN`），该 SQL 语法在 SQL Server / Oracle 上不兼容。
4. **模型 `String` 无长度**：在 MySQL / Oracle 建表报错；SQL Server 的 `VARCHAR` 默认只有 **1 字符**——这是跨库正确建表的硬前提。
5. 上传附件是文件系统路径（存于 `config.upload_dir`，不存库），迁移只影响数据库行，附件引用路径依旧有效；上传目录本身不迁移。

---

## 2. 总体方案

```
db_config.json（数据持久化目录，优先级最高）
        │
        ▼
database.py 解析器：resolve_url() = db_config.json > DATABASE_URL env > sqlite 默认
        │
        ├── get_engine() / get_sessionlocal() / get_db()   ← 全局可切换
        │
        ├── reconfigure_db(cfg)   ← 切换后进程内替换 engine/sessionmaker
        │
        └── current_db_info()     ← 供管理后台展示
```

- 新增 `services/db.py`：多库 URL / 连接参数构建、连接测试。
- 新增 `services/db_migrate.py`：反射源库 → 目标库建表 → 逐表拷贝 → 方言适配 → 备份。
- 新增 `controllers/admin/db.py`：super 权限的查看 / 测试 / 切换 / 备份接口。
- 新增前端 `views/admin/AdminDatabase.vue`，注册进 `Admin.vue` 导航。
- 对 14 个模型的 `String` 无长度列做长度规范化。

---

## 3. 详细实施

### 3.1 配置接入与解析

**`backend/app/config.py`**
- 新增 `db_config_file: str = "./data/db_config.json"`，可被 `DB_CONFIG_FILE` 覆盖。

**`backend/app/database.py`（重构为解析器）**
- `resolve_url()`：优先级 `db_config.json` > `DATABASE_URL` env > `sqlite:///./app.db`；配置文件不存在或非法时回退默认。
- 全局 `_engine` / `_SessionLocal`，并提供：
  - `get_engine()`、`get_sessionlocal()`、`get_db()`（取当前全局 sessionmaker）。
  - `reconfigure_db(cfg)`：构造 URL + connect_args → 新 engine/sessionmaker → 覆盖全局 → 幂等 `create_all` + `_ensure_columns()`。
  - `current_db_info()`：返回当前类型 / 主机 / 库名等（密码脱敏）。
- 说明：保持 `Base` 可导入；无配置文件时行为等价于当前默认 SQLite，不使既有测试 / 导入失败。

**`backend/app/main.py`**
- 改用 `get_engine()` / `get_sessionlocal()`；抽 `recreate_schema(engine)` 供切换后复用（`create_all` + `_ensure_columns()` 幂等）。

**`backend/app/controllers/webhook/feishu_bot.py`**
- `SessionLocal()` 改为通过 `get_sessionlocal()` 获取（避免持有过期引用）。

**`backend/reset_admin_secret.py`**
- 复用 `resolve_url()` 统一 URL 解析。

### 3.2 多库 URL / 连接（新增 `backend/app/services/db.py`）

- `build_url(cfg)` 映射：
  - `sqlite` → `sqlite:///<path>`
  - `mysql` → `mysql+pymysql://user:pass@host:port/db`
  - `postgresql` → `postgresql+psycopg2://user:pass@host:port/db`
  - `mssql` → `mssql+pymssql://user:pass@host:port/db`
  - `oracle` → `oracle+oracledb://user:pass@host:port/db`
- `build_connect_args(dialect)`：
  - SQLite：`check_same_thread=False`
  - MySQL：`charset=utf8mb4`
  - 其它：`pool_pre_ping=True`（SQLite 也可加）
- `test_connection(cfg)`：用一次连接握手验证。
- **`backend/requirements.txt`** 增加：`pymysql`、`psycopg2-binary`、`pymssql`、`oracledb`。
- **`docker/Dockerfile.backend`**：增加环境变量 `DB_CONFIG_FILE=/app/data/db_config.json`。

### 3.3 迁移引擎（新增 `backend/app/services/db_migrate.py`）

1. 用目标配置构造目标 engine，`Base.metadata.create_all` 建全表。
2. 用 `MetaData(reflect)` 反射源库；按外键拓扑排序，逐表 `SELECT` → 显式 `INSERT`（**保留主键**，维护关联）。
3. 方言适配：
   - MSSQL：插入前 `SET IDENTITY_INSERT <table> ON`，结束 `OFF`。
   - Oracle：迁移后重设相关 sequence 到 `max(id)+1`。
   - MySQL / PostgreSQL / SQLite：直接插显式 ID 即可。
4. 目标库已有同名非空表 → 抛错，除非传 `override` 确认。
5. 备份：SQLite 复制 `.db` 文件到 `data/backups/`；其它库提示需自行备份。
6. 迁移全程使用**独立 engine**（不触碰当前线上 engine）；全部成功后再写 `db_config.json` 并调用 `reconfigure_db()`。

### 3.4 后端 API（新增 `backend/app/controllers/admin/db.py`，super 权限）

- `GET  /api/admin/db`：当前库类型 / 连接（密码脱敏）+ 四类驱动安装状态。
- `POST /api/admin/db/test`：测试目标连接（body：type/host/port/database/username/password/sqlite_path）。
- `POST /api/admin/db/switch`：迁移并热切换（同 body + 可选 `override`）。
- `POST /api/admin/db/backup`：备份当前库。

在 `backend/app/controllers/admin/__init__.py` 中注册 `db` 模块。

### 3.5 前端

**`frontend/src/views/admin/AdminDatabase.vue`（新增）**
- 当前库信息卡片（类型 / 主机 / 库名 / 驱动状态）。
- 目标库表单：类型下拉（sqlite/mysql/postgresql/mssql/oracle）、host、port、database、username、password、SQLite 路径。
- 按钮：测试连接、迁移并切换（确认弹窗）、备份。
- 结果 / 进度提示。

**`frontend/src/views/Admin.vue`**
- `superNav` 新增 `{ key: 'database', label: '数据库' }`。
- `sectionMap` 新增 `database: AdminDatabase`，并 import。

**`frontend/src/api.js`**
- 新增 `adminDb`、`adminDbTest`、`adminDbSwitch`、`adminDbBackup`。

### 3.6 模型 String 长度规范化（14 个 `backend/app/models/*.py`）

- 短字段（id 列表 `mcp_ids`/`skill_ids`、手机号、昵称、userid、单行配置等）→ `String(255)`。
- 会长文本（mcp 的 `args`/`env`/`headers`、各 `system_prompt`、附件 `filename`/`extracted_text`、`description` 等）→ `Text` 或较长 `String`。
- 对 SQLite 无副作用（SQLite 忽略长度）；是 MySQL / Oracle / SQL Server 正确建表的前提。

---

## 4. 测试与验证

- 新增 `backend/tests/test_db_config.py`：`build_url`、`resolve_url` 优先级、`_ensure_columns()` 幂等。
- 迁移后跑全量 `pytest`（`python -m pytest backend/tests`）。
- 以 **SQLite → MySQL** 端到端为主做冒烟；PostgreSQL 可选。Oracle / SQL Server 标注需真实环境验证。
- 说明：单进程热切换安全；若后续多 worker / 多实例部署需同步重启（页面上注明）。

---

## 5. 关键风险与对策

| 风险 | 对策 |
|------|------|
| `_ensure_columns()` 的 `ALTER ... ADD COLUMN` 在 MSSQL/Oracle 不兼容 | 迁移目标库用 `create_all` 保证列齐全再拷贝，避免触发；对 `_ensure_columns` 增加方言感知保护（确实缺列时按方言 ALTER） |
| 目标库已有数据被覆盖 | 检测同名非空表，默认拒绝，需 `override` 确认 |
| 热切换后旧长连接 / 多实例不一致 | 单进程安全；多实例需同步重启，页面提示 |
| 驱动缺失导致切换失败 | `test_connection` 前置校验；页面显示驱动安装状态 |

---

## 6. 文件变更清单

**新增**
- `backend/app/services/db.py`
- `backend/app/services/db_migrate.py`
- `backend/app/controllers/admin/db.py`
- `frontend/src/views/admin/AdminDatabase.vue`
- `backend/tests/test_db_config.py`

**修改**
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/controllers/webhook/feishu_bot.py`
- `backend/reset_admin_secret.py`
- `backend/app/controllers/admin/__init__.py`
- `backend/requirements.txt`
- `docker/Dockerfile.backend`
- `frontend/src/views/Admin.vue`
- `frontend/src/api.js`
- `backend/app/models/*.py`（14 个，String 长度规范化）
