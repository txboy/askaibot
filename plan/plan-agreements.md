# 计划：协议（Agreement）功能

> 目标：后台可添加多条协议；前台登录需勾选确认协议，并可点击「查看协议」浏览内容；所有登录方式（手机 / 企微 / 钉钉 / 飞书，含 OAuth 跳回）及已登录会话均强制确认必填协议。

## 交互流程小结

- 后台「协议管理」可对多条协议增删改，每条可设「必须确认」与「启用」。
- 登录页显示每条启用协议的勾选框 + 「《标题》查看」链接（点击弹窗浏览内容）；未勾选禁止登录。
- 所有登录方式（含 OAuth 跳回返回 token）及已登录会话进入主界面时，若存在未确认的必填协议则强制弹窗，确认后才可使用。

## 后端

### 1. 数据模型
新建 `backend/app/models/agreement.py`：
- `Agreement` 表 `agreements`：
  - `id` (Integer, PK, index)
  - `title` (String)
  - `content` (Text, 默认 `""`)
  - `enabled` (Integer, 默认 `1`)
  - `required` (Integer, 默认 `1`)
  - `created_at` (DateTime, server_default=func.now())
  - `updated_at` (DateTime, server_default=func.now(), onupdate=func.now())

在 `backend/app/models/__init__.py` 注册导出 `Agreement` 到 `__all__`。

### 2. 用户确认状态
修改 `backend/app/models/user.py`，为 `User` 增加：
- `agreed_agreement_ids` (String, 默认 `""`)
- `agreed_at` (DateTime, 可空)

在 `backend/app/main.py` 的 `_ensure_columns()` 中，对 `users` 表用 `ALTER TABLE` 补齐这两列（沿用现有迁移模式）：
```python
if "agreed_agreement_ids" not in ucols:
    conn.execute(text("ALTER TABLE users ADD COLUMN agreed_agreement_ids VARCHAR DEFAULT ''"))
if "agreed_at" not in ucols:
    conn.execute(text("ALTER TABLE users ADD COLUMN agreed_at DATETIME"))
```
新表 `agreements` 由 `Base.metadata.create_all(bind=engine)` 自动创建。

### 3. Schemas
`backend/app/schemas.py` 新增：
- `AgreementCreate(BaseModel)`：`title`、`content`(默认 `""`)、`enabled`(默认 `1`)、`required`(默认 `1`)
- `AgreementUpdate(BaseModel)`：`title`/`content`/`enabled`/`required` 均 `Optional`
- `AgreementOut(BaseModel)`：`id`、`title`、`content`、`enabled`、`required`、`created_at`、`updated_at`，`from_attributes = True`
- `AgreementPublic(BaseModel)`：`id`、`title`、`content`、`required`
- `AgreeRequest(BaseModel)`：`agreement_ids: list[int]`

### 4. 后台接口
新建 `backend/app/controllers/admin/agreements.py`（仿 `groups.py` 模式，均依赖 `get_current_admin`）：
- `GET /admin/agreements` → `list[AgreementOut]`
- `POST /admin/agreements` → `AgreementOut`
- `PUT /admin/agreements/{id}` → `AgreementOut`
- `DELETE /admin/agreements/{id}` → `{"ok": True}`

在 `backend/app/controllers/admin/__init__.py` 中：
- import `agreements`
- 加入 `include_router` 循环元组
- 加入 star import 列表

### 5. 前台公开接口
在 `backend/app/controllers/frontend/auth.py` 新增：
- `GET /auth/agreements`（免登录，不依赖 `get_current_user`）：返回启用的协议 `list[AgreementPublic]`
- `GET /auth/agreement-status`（需登录）：返回当前用户尚未确认的**必填**协议 `list[AgreementPublic]`（计算 `enabled and required and id not in user.agreed_agreement_ids`）
- `POST /auth/agree`（需登录）：body `AgreeRequest`；将 `agreement_ids` 并入 `user.agreed_agreement_ids`（逗号分隔存储），并设置 `user.agreed_at = now()`，返回 `{"ok": True}`

工具函数：`_parse_agreed_ids(user) -> set[int]` 用于解析逗号分隔字符串。

### 6. 测试
新增 `backend/tests/test_agreements.py`（仿 `tests/test_groups.py`）：
- 管理员登录 → 增删改查协议
- 公开 `GET /auth/agreements` 返回启用协议
- 登录用户 `agreement-status` 返回未确认必填协议
- `POST /auth/agree` 后 `agreement-status` 为空

## 前端

### 7. `frontend/src/api.js`
新增：
```js
agreements: () => request('/auth/agreements'),
agreementStatus: () => request('/auth/agreement-status'),
acceptAgreement: (ids) => request('/auth/agree', { method: 'POST', body: { agreement_ids: ids } }),
adminAgreements: () => adminRequest('/admin/agreements'),
adminCreateAgreement: (data) => adminRequest('/admin/agreements', { method: 'POST', body: data }),
adminUpdateAgreement: (id, data) => adminRequest(`/admin/agreements/${id}`, { method: 'PUT', body: data }),
adminDeleteAgreement: (id) => adminRequest(`/admin/agreements/${id}`, { method: 'DELETE' }),
```

### 8. 后台管理页
新建 `frontend/src/views/admin/AdminAgreements.vue`（仿 `AdminGroups.vue`）：
- 表格：标题 / 内容（截断）/ 必须确认 / 启用 / 操作
- 顶部「＋ 新建协议」
- 新建 / 编辑弹窗：标题 input、内容 textarea、必须确认 checkbox、启用 checkbox
- 删除：`ConfirmDialog` 确认

修改 `frontend/src/views/Admin.vue`：
- import `AdminAgreements`
- `navItems` 添加 `{ key: 'agreement', label: '协议管理' }`
- `sectionMap` 添加 `agreement: AdminAgreements`

### 9. 协议确认组件
新建 `frontend/src/components/AgreementModal.vue`：
- props：`agreements` (list)、`visible` (bool)、`title`（默认 「协议」）
- 展示协议内容（可滚动）
- 「我已阅读并同意」checkbox（勾选后启用「确认」按钮）
- `emit('confirm', ids)`（当前确认的协议 id 列表）、`emit('cancel')`
- 复用 `ConfirmDialog.vue` / `.modal` / `.modal-mask` 等现有样式

### 10. 登录页 `frontend/src/views/Login.vue`
- `onMounted` 调 `api.agreements()`；若存在启用协议：
  - 在登录面板下方渲染每条协议：`<label class="check"><input type="checkbox" v-model="agreedIds"> 我已阅读并同意 <a @click="viewAgreement(item)">《{{item.title}}》</a></label>`
  - 「查看协议」打开 `AgreementModal`（仅浏览，`:confirmable="false"`）
  - 手机登录 / 企微 / 钉钉 / 飞书「登录」「一键登录」按钮在 `agreedIds` 覆盖所有启用协议前禁用
- `route.query.token`（OAuth 跳回）流程：
  - `setAuth` 后调 `api.agreementStatus()`；若存在未确认必填协议 → 打开 `AgreementModal` 强制接受，确认后调 `api.acceptAgreement(ids)` 再 `router.replace('/')`；否则直接跳转
- 取消登录流程切换 tab 时保持 `agreedIds` 状态

### 11. 已登录会话强制
修改 `frontend/src/composables/useChat.js` 与 `frontend/src/views/Chat.vue`：
- `useChat` 增加：`agreementOpen`、`pendingAgreements`、`acceptPendingAgreement()`、在 `init()` 中加载用户后调 `api.agreementStatus()`，若有必填未确认设置 `pendingAgreements` 并打开 `agreementOpen`
- `Chat.vue` 渲染 `<AgreementModal>`，确认后调用 `acceptPendingAgreement()` 后关闭
- 未确认期间隐藏 / 禁用聊天主界面，或仅显示弹窗并阻止发送（以弹窗遮罩实现即可）

## 验收要点
- 后台可新增/编辑/删除协议，设置「必须确认」「启用」。
- 登录页显示协议勾选框与「查看协议」弹窗；未勾选禁止各登录按钮。
- OAuth 跳回登录与已登录会话均会因未确认必填协议而被弹窗拦截，确认后可正常使用。
