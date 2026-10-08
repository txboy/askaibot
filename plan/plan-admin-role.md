# 简化 RBAC + 审计日志 — 实现方案

## 目标

在管理后台引入三层角色权限（超级管理员 / 部门管理员 / 普通用户）与关键操作审计，满足企业自建（中型几十人）的内控与等保要求。按「角色 + 部门」两维控制，不做细粒度权限矩阵，改动最小。

## 设计决策(已确认)

- **角色模型**：`admins` 表加 `role` 字段（`super` / `dept`）；普通用户仍是 `users` 表聊天账号，不下放后台登录。
- **部门**：新建独立 `departments` 概念，与现有 `user_groups`（资源授权）解耦。
- **部门管理员范围**：仅管本部门用户 + 用量（查看本部门成员、会话/消息/token 用量、管理本部门成员归属）。**不可**删除用户账号、不可改全局设置（接口/工具/协议/系统设置）。
- **审计**：记录关键写操作；仅超级管理员可查看与导出（CSV/JSON）。部门管理员不可见。
- **全局管理接口全部收紧为 super**：现有所有 admin 全局接口从 `get_current_admin` 提升为 `require_super`。

---

## 数据模型

### 变更现有表

| 表 | 新增列 |
|----|--------|
| `admins` | `role` VARCHAR DEFAULT `'super'`；`department_id` INTEGER NULL（dept 绑定部门，super 为空） |
| `users` | `department_id` INTEGER NULL（归属部门，可空=未分配） |

### 新增表

新增 `backend/app/models/department.py`、`backend/app/models/audit_log.py`，并在 `models/__init__.py` 注册：

| 表 | 字段 |
|----|------|
| `departments` | id, name, description, created_at |
| `audit_logs` | id, admin_id, admin_username, admin_role, department_id, action, target_type, target_id, summary(JSON), ip, user_agent, created_at |

迁移：在 `main.py::_ensure_columns` 中补充 `admins.role`、`admins.department_id`、`users.department_id` 的 `ALTER`；新表由 `Base.metadata.create_all` 自动创建。初始 admin 置为 `role='super'`。

---

## 后端

### 鉴权 `backend/app/auth.py`

- `create_admin_token` 的 payload 加入 `role`（读自 admin.role）。
- 新增依赖：
  - `require_super`：`get_current_admin` + `role=='super'`，否则 403。
  - `require_dept`：`role=='dept'` 且持有 `department_id`。
- 保留 `get_current_admin` 作为基础校验。

### 全局管理接口收紧为 super

以下控制器的依赖由 `get_current_admin` 改为 `require_super`：

- `admin/endpoints.py`、`admin/knowledge_bases.py`、`admin/mcp.py`、`admin/skills.py`
- `admin/search.py`、`admin/sms.py`、`admin/wecom_bots.py`、`admin/integrations.py`
- `admin/system.py`、`admin/agreements.py`、`admin/groups.py`
- `admin/users.py` 的 `delete_user`、`list_users`（超管全量）

### 新增接口

**部门管理（仅 super）** `admin/departments.py`：

- `GET /admin/departments` — 列表（含成员数、部门管理员）
- `POST /admin/departments` — 创建
- `PUT /admin/departments/{id}` — 更新
- `DELETE /admin/departments/{id}` — 删除
- `PUT /admin/departments/{id}/admins` — 指定部门管理员（account_id）
- `PUT /admin/users/{id}/department` — 分配用户到部门

**审计日志（仅 super）** `admin/audit.py`：

- `GET /admin/audit-logs` — 分页 + 按 admin/action/target_type/target_id/时间筛选
- `GET /admin/audit-logs/export` — 导出 CSV/JSON

**部门管理员（dept）**：

- `GET /admin/departments/mine/users` — 本部门用户列表（含用量）
- `GET /admin/departments/mine/stats` — 本部门会话/消息/token 用量
- 用户列表兼容：`list_users` 对 dept 仅返回本部门成员并隐藏删除操作

**当前管理员信息**：

- `GET /admin/me` — 返回 `role`、`department_id`（前端据此渲染菜单）

### 审计工具 `backend/app/services/audit.py`

- `audit(db, admin, action, target_type, target_id, summary)`，在关键写操作处调用，写入 `audit_logs`。
- 记录点：登录/登出；管理员增删改与角色/部门调整；用户删除/分配部门；接口/知识库/MCP/技能/搜索/短信/企微/钉钉/飞书/用户组/协议/系统设置增删改；修改密码。

### Schemas `backend/app/schemas.py`

- 新增 `DepartmentOut/Create/Update`、`AuditLogOut`、`AdminMe`。
- 扩展 `AdminUserOut`、`AdminOut`（或登录返回）增加 `role`、`department_id`。

---

## 前端

- `api.js` — 新增 `adminMe`、`departments`（list/create/update/delete）、`adminSetDeptAdmin`、`adminAssignUserDept`、`auditLogs`（list/export）、`adminDeptUsers`、`adminDeptStats`。
- `views/Admin.vue` — 登录后按 role 渲染菜单：
  - super：现全部菜单 +「部门管理」「审计日志」
  - dept：仅「本部门用户」「本部门用量」「修改密码」
- 新增 `views/admin/AdminDepartments.vue`：部门 CRUD + 指定部门管理员 + 分配用户。
- 新增 `views/admin/AdminAudit.vue`：日志列表 + 筛选 + 导出。
- `views/admin/AdminUsers.vue`：对 dept 隐藏删除/全局操作，仅显示本部门成员，新增「部门」列。

---

## 测试与验证

新增 `backend/tests/test_rbac.py`、`backend/tests/test_audit.py`：

- super 可进全局接口，dept 访问全局接口返回 403。
- dept 越权访问他部门用户/接口返回 403。
- dept 不可删除用户账号。
- 分配用户到部门、指定部门管理员。
- 关键写操作产生 `audit_logs`；导出仅 super 可用；分页与筛选。
- 复用现有 TestClient 夹具，运行 `pytest` 回归验证。

---

## 实施顺序

1. models（Department / AuditLog / admins+users 加列）+ 注册
2. auth.py（role payload、`require_super` / `require_dept`）
3. main.py（`_ensure_columns` 迁移 + seed super）
4. audit 工具函数
5. 路由（departments / audit-logs / users 按权 / dept 用量 / admin/me）
6. 全局 admin 控制器收紧为 `require_super`
7. 前端（api.js、Admin.vue、AdminDepartments、AdminAudit、AdminUsers）
8. 测试 + README/迁移说明
