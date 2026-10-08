# 功能详解

## 聊天管线（`POST /api/chat`）

请求体 `ChatRequest`：`conversation_id`、`content`、`attachment_ids[]`、`endpoint_id?`、`model?`、`web_search?`、`knowledge_base_id?`。

### 流式前的准备（同步）

1. **限额检查** `_enforce_token_quota`：有效限额为 个人 > 部门 > 系统（取第一个正值）；当日用量 ≥ 限额返回 **HTTP 429**。
2. 校验会话归属（否则 404）。
3. **接口选择** `_resolve_endpoint`：显式 `endpoint_id` 需存在、启用且对用户可见；否则取第一个启用接口（按 `is_default desc, id asc`）。
4. **模型选择** `_resolve_model`：请求 `model` 或接口模型列表首项；为空报 400。
5. 绑定附件、保存用户消息、刷新会话 `updated_at`。
6. 加载历史并构建 OpenAI `messages`（图片转 `image_url` base64，文档注入提取文本）。
7. **系统提示词** `resolve_system_prompt`，优先级：机器人 > 平台专属（企微/钉钉/飞书）> 接口 `system_prompt` > 全局 `system_prompt`。
8. 前端知识库：仅当传入的 `knowledge_base_id` 启用、`mode=frontend` 且可见。
9. 联网搜索：需已配置 provider、用户有权且（显式开启或 `search_auto`）。
10. 组装 `{model, messages, stream: true, stream_options: {include_usage: true}}`。

### SSE 事件格式

每帧 `data: <json>\n\n`：

- `{"delta": "文本"}` — 增量内容
- `{"status": "searching"}` — 联网搜索中
- `{"status": "tool", "server": "名称"}` — 调用 MCP/技能/知识库工具中
- `{"error": "消息"}` — 上游或异常错误
- `{"done": true}` — 结束（助手消息已落库）

### 工具与多轮调用

`_build_tool_plan` 汇总工具（命名空间前缀区分）：MCP（`mcp__服务器__工具`）、技能（`skill__技能__工具`，其 `SKILL.md` 正文作为系统消息注入）、LLM 模式知识库（`kb__名称__id__retrieve`）、联网搜索。最多 3 轮；**仅第 0 轮下发 tools**；模型返回的 `tool_calls` 由 `_run_tool_call` 路由执行，结果作为 `role=tool` 消息回填。上游 `usage.total_tokens` 记入助手消息 `tokens`。

## 登录方式

- **手机号 + 验证码**：本地模拟（`SMS_MOCK=true` 返回/打印验证码）或对接阿里云/腾讯云短信；发送前可启用验证码防刷（内置图片 / GeeTest / 腾讯 / 阿里云）。
- **企业微信**：网页授权 OAuth 与扫码；未配置时自动降级为模拟模式。
- **钉钉**：OAuth + App 内一键登录（unionId→userId）。
- **飞书**：OAuth + App 内一键登录。

OAuth 回调以 `?token=` 重定向前端，前端换取用户资料并校验协议。

## 会话与消息

多会话管理（新建/重命名/删除），消息持久化到数据库；会话可关联 MCP 与技能（`mcp_ids` / `skill_ids`）。删除会话级联删除其消息与附件。

## 文件上传

`POST /api/upload`：限制大小（默认 20MB），按类型识别——图片以 `image_url`（base64）发送；文本 / PDF / Word / Excel 自动提取文本后嵌入消息。附件经 `GET /api/files/{id}` 鉴权读取。

## 三层 RBAC 与审计

| 角色 | 权限 |
|------|------|
| **super** 超级管理员 | 全部后台功能，含部门/管理员/审计 |
| **dept** 部门管理员 | 仅本部门成员与用量，不能改全局设置、不能删用户 |
| **user** 普通用户 | 聊天终端用户，无后台权限 |

- 部门：`departments` 表，用户经 `users.department_id` 归属；部门管理员在「部门管理」指派。
- 全局管理接口默认仅 `super` 可访问。
- 审计日志：关键写操作自动写入 `audit_logs`，仅超级管理员可查看/筛选/导出 CSV。

## 用户组与资源授权

`user_groups` 管理成员，`group_grants` 将资源授权给组。资源类型：`endpoint`、`knowledge_base`、`mcp`、`search`、`skill`。可见性支持 `global`（全部用户）或 `group`（仅授权组）。

## 知识库

支持 **Dify** 与 **RAGFlow**。两种模式：

- `frontend`：用户在前端选择知识库，检索结果注入上下文。
- `llm`：作为工具交给模型自主调用（`kb__...__retrieve`）。

## MCP 工具

支持 HTTP（streamable）与 stdio 传输；两种模式 `llm`（自动注入工具）/ `frontend`（用户选择）。工具列表缓存 5 分钟，可测试/刷新。

## 技能包（Skill）

上传 zip/tar.gz（含带 YAML frontmatter 的 `SKILL.md`），解析名称/描述/工具，`SKILL.md` 正文作为系统提示词。工具在本地软沙箱执行（`subprocess`，超时 `SKILL_TIMEOUT`，CPU 限制，净化环境变量）。范围：`global` / 按用户 / 按用户组。

## 联网搜索

服务商：Tavily / Bing / SearXNG / DuckDuckGo。支持手动开关与 `search_auto` 自动触发；结果以「以下是联网搜索结果…」注入。

## Token 限额

有效限额优先级：个人 `users.token_limit_daily` > 部门 `departments.token_limit_daily` > 系统 `settings.token_limit_daily`。当日用量为当天（本地零点起）用户所有消息 `tokens` 之和。超限拦截聊天（429）。

## 协议（Agreement）

管理员维护协议文本，可设 `required`（登录前必读同意）与 `enabled`。用户登录后如存在未同意的必读协议，强制弹窗并记录 `users.agreed_agreement_ids` / `agreed_at`。

## 机器人接入（企微 / 钉钉 / 飞书）

`wecom_bots` 表统一承载三渠道机器人，`provider` 区分。每个机器人可绑定接口 + 模型、系统提示词、知识库、MCP、技能、联网开关。回调：

- 企微：`/api/wecom/bot/{bot_id}/callback`，加解密 + 签名校验。
- 钉钉：`/api/dingtalk/bot/{bot_id}/callback`，`check_url` 事件处理。
- 飞书：`/api/feishu/bot/{bot_id}/callback`，AES 解密、`event_id` 去重、异步处理。

三渠道共用 `services/wecom_bot.py::generate_reply` 生成带工具调用的回复。

## 数据库热切换

后台「系统管理 → 数据库」可在 SQLite / MySQL / PostgreSQL / MSSQL / Oracle 之间切换，先测试连接、必要时备份、迁移数据（附件文件不迁移），再热切换引擎。详见 [部署与运维](deployment.md)。
