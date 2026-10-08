# 数据模型

数据库表由 `backend/app/models/` 定义，主键统一为 `Integer + Identity()`。`models/types.py` 提供 `OrEmptyStr` / `OrEmptyText`，在绑定/读取时把空串与 `NULL` 归一化（兼容 Oracle 把 `''` 视作 `NULL`）。模型间未声明 SQLAlchemy `relationship()`，关联通过外键列与显式查询完成。

## 表清单

### users
| 字段 | 说明 |
|------|------|
| id | 主键 |
| nickname | 昵称，默认 `用户` |
| avatar / assistant_name / assistant_avatar | 头像、助手昵称与形象 |
| phone / wecom_userid / dingtalk_userid / feishu_userid | 各渠道身份（唯一索引，MSSQL 过滤 NULL） |
| agreed_agreement_ids / agreed_at | 已同意协议 |
| department_id | 所属部门 |
| token_limit_daily | 个人每日 Token 限额 |
| created_at | 注册时间 |

### admins
`id`、`username`（唯一）、`password_hash`、`role`（`super`/`dept`）、`department_id`。

### departments
`id`、`name`、`description`、`token_limit_daily`、`created_at`。

### conversations
`id`、`user_id`→users、`bot_id`（可空，关联机器人）、`title`（默认 `新对话`）、`model`、`mcp_ids`、`skill_ids`、`created_at`、`updated_at`。

### messages
`id`、`conversation_id`→conversations、`role`（默认 `user`）、`content`、`tokens`（默认 0）、`endpoint_id`→api_endpoints（可空）、`created_at`。

### attachments
`id`、`user_id`、`conversation_id`、`message_id`、`filename`、`stored_name`、`content_type`、`kind`（`image`/`text`/`doc`）、`extracted_text`、`size`、`created_at`。

### api_endpoints
`id`、`name`、`base_url`、`api_key`、`models`（逗号/换行列表）、`system_prompt`、`enabled`、`is_default`、`scope`（`global`/`group`）、时间戳。

### knowledge_bases
`id`、`name`、`provider`（`dify`/`ragflow`）、`base_url`、`api_key`、`dataset_ids`、`top_k`（默认 5）、`mode`（`frontend`/`llm`）、`description`、`enabled`、`scope`、`created_at`。

### mcp_servers
`id`、`name`、`description`、`transport`（`http`/`stdio`）、`url`、`headers`（JSON）、`command`、`args`（JSON）、`env`（JSON）、`mode`（`llm`/`frontend`）、`enabled`、`scope`、时间戳。

### skills / skill_access
- `skills`：`id`、`name`、`description`、`dir_path`、`content`（SKILL.md 正文）、`tools`（JSON）、`scope`（`global`/`user`）、`enabled`、时间戳。
- `skill_access`：`id`、`skill_id`、`user_id`（按用户授权）。

### user_groups / user_group_members / group_grants
- `user_groups`：`id`、`name`、`description`、`created_at`。
- `user_group_members`：`id`、`group_id`、`user_id`（唯一约束）。
- `group_grants`：`id`、`group_id`、`resource_type`（`endpoint`/`knowledge_base`/`mcp`/`search`/`skill`）、`resource_id`。

### agreements
`id`、`title`、`content`、`enabled`（默认 1）、`required`（默认 1）、`created_at`、`updated_at`。

### wecom_bots
`id`、`name`、`provider`（`wecom`/`dingtalk`/`feishu`）、`corp_id`、`secret`、`agent_id`、`token`、`aes_key`、`kb_ids`、`mcp_ids`、`skill_ids`、`web_search`、`system_prompt`、`endpoint_id`、`model`、`enabled`、`created_at`。

### bot_events
`id`、`bot_id`、`event_id`（唯一，去重）、`created_at`。

### audit_logs
`id`、`admin_id`、`admin_username`、`admin_role`、`department_id`、`action`、`target_type`、`target_id`、`summary`、`ip`、`user_agent`、`created_at`。

### settings
单行配置表（id=1），字段较多，涵盖：

- 基础：`base_url`、`api_key`、`default_model`
- 系统提示词：`system_prompt`、`wecom_system_prompt`、`dingtalk_system_prompt`、`feishu_system_prompt`
- 渠道凭据：企微 / 钉钉 / 飞书
- 品牌：`logo_path`、`favicon_path`、`site_title`、`assistant_name`、`assistant_avatar`
- 后台：`admin_secret_enabled`、`admin_secret`
- 外观：`theme`、`debug_mode`
- 短信与验证码：`sms_*`、`*_captcha_*`（builtin/geetest/tencent/aliyun）
- 搜索：`search_provider`、`search_api_key`、`search_base_url`、`search_auto`、`search_scope`
- 限额：`token_limit_daily`

## 关系概览

```
users ─< conversations ─< messages ─< attachments
users ─< attachments
users ─< skill_access >─ skills
users ─< user_group_members >─ user_groups ─< group_grants
departments ─< users
admins ─< audit_logs
wecom_bots ─< conversations
wecom_bots ─< bot_events
```

## 迁移

无需手工执行 SQL：应用启动时 `main.py` 的 `recreate_schema` 会自动建表、补列，并对 Oracle 修复主键自增；数据库切换后同样调用。详见 [后端实现](backend.md) 与 [部署与运维](deployment.md)。
