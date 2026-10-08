# 前端实现

前端位于 `frontend/`，Vue 3（`<script setup>` SFC）+ Vite SPA。未使用 Pinia/Vuex：全局状态由 `store.js` 与 `composables/useChat.js` 中的模块级 `reactive`/`ref` 承担。

## 入口与路由

- `main.js`：创建应用，注册 FontAwesome 全局组件与一组 solid 图标，引入 `style.css`，安装路由并挂载到 `#app`。
- `App.vue`：渲染 `<router-view />`，挂载时拉取主题（`getTheme` → `applyTheme`）与站点信息（`site`，设置标题与 favicon）。
- `router/index.js`（`createWebHistory`）：

| 路径 | 视图 | 说明 |
|------|------|------|
| `/` | Chat | 需登录 |
| `/login` | Login | 登录 |
| `/admin` | Admin | 管理后台 |
| `/404` | NotFound | |
| `*` | NotFound | 兜底 |

导航守卫 `beforeEach`：

1. 访问 `/admin` 时调用 `api.adminAccess(to.query.r)`；失败则跳 `/404`——这是后台随机地址机制（开启后需 `?r=<secret>`）。
2. `meta.requiresAuth` 且无 token：企业微信 UA（`/wxwork/i`）直接跳 `window.location.replace('/api/auth/wecom/oauth')`，否则跳 `/login`。
3. 已登录访问 `/login` 时跳 `/`。

## 全局状态 `store.js`

`reactive` 单例，全部从 `localStorage` 初始化：

- `token` / `user` — 用户 JWT 与资料
- `adminToken` / `adminRole` — 管理员 JWT 与角色（`super` / `dept`）

方法：`setAuth`、`setUser`、`logout`、`setAdminToken`、`setAdminRole`、`logoutAdmin`。

## API 客户端 `api.js`

`BASE = '/api'`。两个封装：`request`（默认带用户 token）与 `adminRequest`（带管理员 token），非 2xx 抛 `Error(detail)`。

按区域划分：

- 认证/资料：`captcha`、`smsSend`、`smsVerify`、`wecomQrcode`、`dingtalkQrcode`、`dingtalkFreeLogin`、`feishuQrcode`、`feishuFreeLogin`、`me`、`updateProfile`、`updatePhone`、`uploadAvatar`、`uploadAssistantAvatar`
- 会话：`conversations`、`createConversation`、`renameConversation`、`deleteConversation`、`messages`、`updateConversationMcp`、`updateConversationSkills`
- 资源：`endpoints`、`knowledgeBases`、`mcpServers`、`skills`、`quota`
- 站点配置：`getTheme`、`getDebug`、`getSms`、`getWecom`、`getDingtalk`、`getFeishu`、`getSearch`、`site`
- 管理：`adminLogin`、`adminMe`、`adminAccess`、接口/品牌/主题/系统/DB/SMS/搜索/知识库/MCP/技能/机器人/用户/用户组/协议/部门/管理员/审计等全套 CRUD

独立导出：

- `authFetchBlob(id)` — 带鉴权获取附件并返回对象 URL（图片缩略图）。
- `uploadFile(file)` — 上传文件。
- `streamChat({...})` — 流式聊天（见下）。

### `streamChat` SSE 解析

请求体 `{conversation_id, content, attachment_ids, endpoint_id, model, web_search, knowledge_base_id}`。用 `res.body.getReader()` + `TextDecoder` 读流，按 `\n` 拆行，仅处理 `data:` 前缀行，`JSON.parse(line.slice(5))`；解析失败静默跳过。事件分发：

- `{delta}` → `onDelta`（追加文本）
- `{error}` → `onError`
- `{status}`（`searching` / `tool`）→ `onStatus`
- `{done}` → `onDone`

## 视图

- **Login.vue**：多标签登录（手机 / 企微 / 钉钉 / 飞书，按后端配置显示）。手机登录含验证码防刷（图片 / GeeTest v4 / 腾讯 / 阿里云）与 60s 倒计时；企微/钉钉/飞书渲染二维码或模拟扫码，钉钉/飞书在 App 内支持“一键登录”。含协议勾选与 `?token=` 回调处理。
- **Chat.vue**：薄壳，逻辑在 `useChat`。渲染侧边栏、消息列表、输入区、四个选择弹窗（接口/知识库/MCP/技能）、资料弹窗、确认框、协议弹窗。窄屏侧边栏变抽屉。
- **Admin.vue**：后台外壳。未登录显示登录卡；登录后 `adminMe` 取角色。**角色化左侧导航**：
  - 部门管理员：本部门用户、本部门用量、修改密码。
  - 超级管理员：首页 + 四个可折叠分组——用户管理（用户列表/部门/管理员/用户组/改密）、工具接入（接口/短信/搜索/MCP/技能/知识库）、渠道接入（企微/钉钉/飞书）、系统管理（系统设置/数据库/审计/协议）。
- **NotFound.vue**：居中 404 页。

## 聊天模块

逻辑集中在 `composables/useChat.js`（模块级单例），组件在 `components/chat/`：

- **ChatSidebar.vue**：Logo、新建对话、会话列表（双击重命名、悬停删除）、**每日 Token 限额卡片**（进度条，剩余 ≤10% 或为 0 时变红）、用户栏（资料/退出）。
- **MessageList.vue**：欢迎态、消息头像与气泡、助手消息用 `MarkdownContent` 渲染 markdown、用户附件渲染图片（`AttachmentImage`）或文件标签、状态提示（"正在联网搜索…"/"正在调用 MCP 工具…"）、流式光标 `▍`。
- **ChatComposer.vue**：模型 chip、联网开关、知识库/MCP/技能 chip、待发送附件、自适应输入框，Enter 发送 / Shift+Enter 换行。
- 选择弹窗：`EndpointPicker`、`KnowledgeBasePicker`、`McpPicker`、`SkillPicker`。
- 流式发送 `send`：乐观插入用户消息与助手占位消息，`streamChat` 回调追加文本、更新状态，结束后刷新会话与限额。

## 管理页面 `views/admin/`

| 文件 | 说明 |
|------|------|
| `AdminDashboard.vue` | 首页统计卡（用户/会话/消息/接口/附件 + 今日/本月/总 Token）与接口用量表 |
| `AdminUsers.vue` | 用户列表；设置每日 Token 限额、删除用户 |
| `AdminGroups.vue` | 用户组 CRUD，管理成员与资源授权（接口/知识库/MCP/搜索/技能） |
| `AdminAgreements.vue` | 协议 CRUD（必读 `required`、启用 `enabled`） |
| `AdminDepartments.vue` | 部门 CRUD、部门限额、指派部门管理员、分配用户 |
| `AdminAdmins.vue` | 管理员账号 CRUD（角色/部门/重置密码） |
| `AdminAudit.vue` | 审计日志筛选、分页、导出 CSV |
| `AdminDeptStats.vue` | 部门管理员查看本部门成员与用量 |
| `AdminEndpoints.vue` | LLM 接口 CRUD + 可见范围设置 |
| `AdminSms.vue` | 短信服务商与验证码防刷配置 |
| `AdminSearch.vue` | 联网搜索服务商配置 + 范围 |
| `AdminMcp.vue` | MCP 服务器 CRUD（HTTP/stdio、工具发现/刷新） |
| `AdminSkill.vue` | 技能包上传/编辑/测试/删除 |
| `AdminKnowledge.vue` | 知识库 CRUD（Dify/RAGFlow、检索测试） |
| `AdminWecom.vue` / `AdminDingtalk.vue` / `AdminFeishu.vue` | 各渠道基础配置 + 登录指引 + `BotManager` |
| `AdminSystem.vue` | 主题、调试、站点标题、助手默认名/头像、全局系统提示词、系统限额、favicon/logo、后台随机地址 |
| `AdminDatabase.vue` | 当前数据库信息、备份、切换数据库（测试 + 迁移切换） |
| `AdminPassword.vue` | 修改管理员密码 |
| `BotManager.vue` | 各渠道机器人 CRUD（凭据、绑定接口/模型、系统提示词、知识库/MCP/技能/联网、回调地址） |

## 通用组件

- `components/`：`AgreementModal`、`AttachmentImage`、`ConfirmDialog`、`Logo`、`MarkdownContent`（代码块复制）、`ProfileModal`（昵称/头像/助手形象/改绑手机）、`HelloWorld`（Vite 残留，未使用）
- `components/chat/`：`ChatComposer`、`ChatSidebar`、`EndpointPicker`、`KnowledgeBasePicker`、`McpPicker`、`SkillPicker`、`MessageList`
- `components/admin/`：`LoginGuide`（各渠道登录配置指引）、`UserScopeControl`（全局/按用户组范围）

## 主题与样式

- `theme.js`：`VALID = ['warm','cool','tech']`，`applyTheme(t)` 设置 `<html data-theme>`，非法值回退 `warm`。
- `style.css`：`@font-face`（`ZiHunBianTaoTi-2`，见 `public/fonts/`）；三套 `:root[data-theme]` 变量——**warm**（默认，奶油底 `#fbf6ef` + 暖橙 `#e0804a`）、**cool**（蓝灰 + 蓝 `#4a7dbd`）、**tech**（暗色 `#0d1117` + 薄荷 `#00d4a8`）。
- 设计变量：`--bg`、`--bg-sidebar`、`--surface`、`--primary`、`--text`、`--text-muted`、`--border`、`--danger`、`--code-bg`、`--radius`、`--shadow` 等；含 `.btn` / `.input` / `.modal` / `.md-body` / `.code-wrap` 等全局样式。管理后台大量类（`.card`/`.table`/`.nav-*` 等）在 `Admin.vue` 的非 scoped 样式中定义。

## 工具与组合式函数

- `utils/markdown.js`：配置 `markdown-it`（linkify、breaks、highlight.js），导出 `renderMarkdown`。
- `composables/useChat.js`：聊天状态与全部动作（`init`、`send`、会话/附件/MCP/技能/知识库操作、`logout` 等）。
- `composables/useConfirm.js`：Promise 化的确认框 `askConfirm`。
