# Token 限额 + 剩余额度显示 — 实现方案

## 目标

为网页聊天引入**每日 token 限额**，三级配置（系统级 / 部门级 / 个人级），个人 > 部门 > 系统，三级都未设置则不限额；用户触达限额后**硬性拦截**，聊天页**有条件展示剩余额度**。

## 设计决策(已确认)

- **统计周期**：每日（本地零点重置），与现有「今日 Token」统计口径一致。
- **触达行为**：硬性拦截（达到/超过限额拒绝新请求，返回 429）。
- **作用入口**：仅网页聊天（`/api/chat`）；企微/钉钉/飞书机器人不在此列。
- **优先级**：对单个用户，`个人 > 部门 > 系统`，取第一个正数；全空则不限额。
- **语义**：三级各自是该用户的「默认每日上限」，不是共享总池。
- **前端显示**：仅当 `limit != null` 时在聊天页展示「今日 Token 剩余 X / Y」，不限额则不显示。

---

## 数据模型（含迁移）

| 表 | 新增列 |
|----|--------|
| `settings` | `token_limit_daily` INTEGER NULL（NULL/0=未设置） |
| `departments` | `token_limit_daily` INTEGER NULL |
| `users` | `token_limit_daily` INTEGER NULL |

迁移：在 `main.py::_ensure_columns` 中为三表补充 `ALTER ... ADD COLUMN token_limit_daily INTEGER`。

---

## 后端

### 核心服务 `backend/app/services/quota.py`

- `effective_token_limit(db, user) -> int | None`：按 个人>部门>系统 取第一个正数；全无返回 `None`。
- `used_tokens_today(db, user_id) -> int`：复用 `users.py::_user_out` 口径——该用户所有会话的 `messages.tokens` 之和，且 `created_at >= 本地今日零点`。
- `token_limit_status(db, user) -> dict`：返回 `{"limit": int|None, "used": int, "remaining": int|None}`（`remaining = max(0, limit-used)`，limit 为 None 时为 None）。

### 聊天拦截 `frontend/chat.py::chat`

在函数**开头**（`_save_user_message` 之前）执行：

```python
from app.services import quota as quota_core
limit = quota_core.effective_token_limit(db, user)
if limit is not None:
    used = quota_core.used_tokens_today(db, user.id)
    if used >= limit:
        raise HTTPException(status_code=429, detail="今日 Token 限额已用完，请明日再试或联系管理员")
```

放在落库前，避免拦截后仍写入一条空用户消息。前端 `streamChat` 已处理 `!res.ok` 并展示 `detail`，无需改前端核心逻辑。

### 额度状态接口 `frontend/quota.py`

- `GET /api/quota`（`get_current_user`）→ `quota_core.token_limit_status(db, user)`。
- 在 `main.py` 注册：`app.include_router(quota.router, prefix="/api")`。

### Schemas `backend/app/schemas.py`

- `SystemOut/SystemUpdate`：加 `token_limit_daily: Optional[int] = None`。
- `DepartmentOut/Create/Update`：加 `token_limit_daily`。
- `AdminUserOut`：加 `token_limit_daily`、`token_limit_effective`。
- 新增 `QuotaInfo`：`limit: Optional[int]; used: int; remaining: Optional[int]`。

### Admin 接口

- `admin/system.py`：`get_system/update_system` 处理 `token_limit_daily`（系统级）。
- `admin/departments.py`：`_dept_out`、create、update 处理 `token_limit_daily`（部门级）。
- `admin/users.py`：
  - `_user_out` 增加 `token_limit_daily` 与 `token_limit_effective`（调用 `quota_core.effective_token_limit`）。
  - 新增 `PUT /admin/users/{user_id}/token-limit`（仅 `require_super`）设置个人限额。

---

## 前端

- `api.js`：
  - `quota: () => request('/quota')`
  - `adminSetUserTokenLimit: (id, limit) => adminRequest(`/admin/users/${id}/token-limit`, { method: 'PUT', body: { token_limit_daily: limit } })`
- `useChat.js`：
  - 新增 `const quota = ref(null)`。
  - `init()` 拉取 `quota.value = await api.quota()`（失败不阻塞）。
  - `send()` 的 `finally` 中重新拉取 `quota`（保持剩余额度实时）。
  - `useChat()` 返回值暴露 `quota`。
- `ChatComposer.vue`：
  - 在 `composer-row` 上方增加一条提示：**仅当 `quota.limit != null`** 时显示 `今日 Token 剩余 X / Y`；剩余低（≤10% 或 0）时用 `--danger` 色。
- `AdminSystem.vue`：增加「系统每日 Token 限额」输入（0=不限）。
- `AdminDepartments.vue`：创建/编辑增加「部门每日 Token 限额」。
- `AdminUsers.vue`：显示 `今日已用 / 有效限额`；super 可编辑个人限额。

---

## 测试与验证

新增 `backend/tests/test_quota.py`：

- 优先级：个人>部门>系统，全空 → `None`。
- `used_tokens_today` 计算正确（含今日边界）。
- `token_limit_status` 返回 `limit/used/remaining`；不限额时 `limit=None`。
- 已达限额时 `/api/chat` 返回 429；未达限额可正常流式（复用现有 mock 流式）。
- `/api/quota` 返回正确结构。
- `test_rbac.py`/`test_audit.py` 及全量 `pytest` 回归。

前端：`npm run build` 通过；手动验证有/无限额两种显示状态。

---

## 实施顺序

1. 三表加列 + `_ensure_columns` 迁移
2. `services/quota.py` + 单测
3. `chat.py` 加入校验 + `GET /api/quota` 路由注册
4. Admin 接口（system/departments/users）+ schemas
5. 前端（api.js / useChat / ChatComposer / AdminSystem / AdminDepartments / AdminUsers）
6. `test_quota.py` + 前后端回归
