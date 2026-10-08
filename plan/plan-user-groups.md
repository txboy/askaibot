# 用户组(User Groups)按组授权 — 实现方案

## 目标

在管理后台新增「用户组」功能：一个用户可属于多个用户组；接口、知识库、MCP、联网搜索、技能包可「按组授权」。

## 设计决策(已确认)

- **默认可见性**：每个资源独立 `scope` 字段（全部=`global` / 按组=`group`），默认 `global`，兼容现有行为。
- **配置入口**：用户组页（集中管理成员 + 各类资源授权） + 各资源管理页（「可见范围」选择器），数据互为镜像。
- **技能**：一并纳入用户组模型，同时保留现有 `user`(per-user) 兼容。
- **搜索**：开关式（单一全局 provider，按组开/关）。

---

## 数据模型

新增 `backend/app/models/user_group.py`，并在 `models/__init__.py` 注册：

| 表 | 字段 |
|----|------|
| `user_groups` | id, name, description, created_at |
| `user_group_members` | id, group_id(FK), user_id(FK)，唯一(group_id, user_id) |
| `group_grants` | id, group_id(FK), resource_type(`endpoint`/`knowledge_base`/`mcp`/`search`/`skill`), resource_id(搜索为 0) |

现有模型加 `scope` 列（default `global`）：

- `models/api_endpoint.py` → `ApiEndpoint.scope`
- `models/knowledge_base.py` → `KnowledgeBase.scope`
- `models/mcp_server.py` → `McpServer.scope`
- `models/skill.py` → `Skill.scope` 扩展支持 `group`

`models/setting.py`（settings 表）加 `search_scope` 列（default `global`）。

迁移：在 `main.py::_ensure_columns` 中补充新列；新表由 `Base.metadata.create_all` 自动创建。

---

## 后端

### 服务层 `backend/app/services/groups.py`

- `user_group_ids(db, user_id) -> list[int]`：返回用户所属组 id 列表（支持多组）。
- `filter_accessible(db, user_id, resource_type, rows) -> list`：过滤出 `scope=global` 或用户所在组已授权的资源。
- `group_ids_for_resource(db, resource_type, resource_id) -> list[int]`：读取某资源被授权给哪些组。
- `set_resource_grants(db, resource_type, resource_id, group_ids)`：写某资源授权的组集合（先删后插）。
- `can_search(db, user_id, setting) -> bool`：搜索 provider 已配置，且（`search_scope=global` 或 用户所在组被授予搜索）。

### Frontend 接口（对用户侧强制）

- `frontend/endpoints.py` — `/api/endpoints`、`/api/knowledge-bases` 使用 `filter_accessible` 过滤。
- `frontend/mcp.py` — `/api/mcp` 使用 `filter_accessible` 过滤。
- `frontend/uploads.py` — `/config/search` 的 `enabled` 加入 `can_search`。
- `frontend/skills.py` — `skill_core.user_skills` 增加 group scope。
- `frontend/chat.py`：
  - `_resolve_endpoint`：校验 endpoint 对当前用户可见，否则返回 400「接口不可用」。
  - `_resolve_frontend_kb`：增加 `user` 参数并校验可见性。
  - `_build_tool_plan`：过滤 MCP（llm + 选中的 frontend）、知识库（llm）、技能（按用户可见集合）。
  - `_should_search`：叠加 `can_search` 判定。

### Admin 接口

- 新增 `controllers/admin/groups.py`：
  - `GET /admin/groups` — 组列表（含 member_ids、member_count、grants 按类型分组）。
  - `POST /admin/groups` — 创建（name/description/member_ids/grants）。
  - `PUT /admin/groups/{id}` — 更新（同创建字段）。
  - `DELETE /admin/groups/{id}` — 删除（级联删除 members 与 grants）。
  - 在 `controllers/admin/__init__.py` 注册。
- 各资源管理控制器返回/接收 `scope` + `group_ids`：
  - `admin/endpoints.py`、`admin/knowledge_bases.py`、`admin/mcp.py`、`admin/skills.py`、`admin/search.py`。

### Schemas `backend/app/schemas.py`

- 新增 `GroupOut`、`GroupCreate`、`GroupUpdate`。
- `EndpointOut/Create/Update`、`KnowledgeBaseOut/Create/Update`、`McpServerOut/Create/Update`、`SkillOut/Update`、`SearchOut/Update` 增加 `scope`（`group_ids` 可选）。

---

## 前端

- `views/Admin.vue` — 导航新增「用户组」，引入 `AdminGroups.vue`。
- 新增 `views/admin/AdminGroups.vue`：
  - 组列表表格（名称、描述、成员数、操作）。
  - 创建/编辑弹窗：名称、描述；成员多选（`api.adminUsers()`）；按类型勾选接口/知识库/MCP/技能 + 搜索开关（分别用 admin 列表接口取数据）。
  - 删除用 `ConfirmDialog`。
- 资源页 `AdminEndpoints`、`AdminKnowledge`、`AdminMcp`、`AdminSkill`、`AdminSearch` — 增加「可见范围（全部/按组）」选择器，按组时展示组多选（`api.adminGroups()`）。
- `api.js` — 补充 `adminGroups`、`adminCreateGroup`、`adminUpdateGroup`、`adminDeleteGroup`。
- Chat 侧无需改动（选择器数据来自已按组过滤的 `/api/*`）。

---

## 测试与验证

新增 `backend/tests/test_groups.py`：

- 组 CRUD、用户多组归属、授权写入。
- 端到端授权过滤：`/api/endpoints`、`/api/knowledge-bases`、`/api/mcp` 按 scope+组过滤。
- 搜索开关：`/config/search` 的 `enabled` 随组授权变化。
- chat 越权拦截：未授权 endpoint / kb / mcp 被拒绝。
- 技能 group scope。

运行 `pytest` 回归验证。
