# API 参考

所有接口前缀 `/api`。用户接口使用 `Authorization: Bearer <user token>`；管理接口使用管理员 JWT。响应非 2xx 时 body 为 `{"detail": "错误信息"}`。

## 认证 `/api/auth`

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/auth/captcha` | 否 | 获取验证码挑战 |
| POST | `/auth/sms/send` | 否 | 发送短信验证码（模拟模式返回 `debug_code`） |
| POST | `/auth/sms/verify` | 否 | 手机号 + 验证码登录，返回 Token |
| GET | `/auth/me` | 用户 | 当前用户信息 |
| PUT | `/auth/profile` | 用户 | 修改昵称 / 助手名 |
| POST | `/auth/avatar?target=user\|assistant` | 用户 | 上传头像 |
| PUT | `/auth/phone` | 用户 | 绑定手机号 |
| GET | `/auth/wecom/qrcode` `\| /oauth \| /callback` | 否 | 企微登录 |
| GET | `/auth/dingtalk/qrcode` `\| /oauth \| /callback` | 否 | 钉钉登录 |
| POST | `/auth/dingtalk/free-login` | 否 | 钉钉 App 内一键登录 |
| GET | `/auth/feishu/qrcode` `\| /oauth \| /callback` | 否 | 飞书登录 |
| POST | `/auth/feishu/free-login` | 否 | 飞书 App 内一键登录 |
| GET | `/auth/agreements` | 否 | 启用的协议列表 |
| GET | `/auth/agreement-status` | 用户 | 待同意的必读协议 |
| POST | `/auth/agree` | 用户 | 记录已同意协议 |

## 会话与消息 `/api/conversations`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/conversations` | 会话列表（按更新时间倒序） |
| POST | `/conversations` | 新建会话 |
| PUT | `/conversations/{id}` | 重命名 |
| DELETE | `/conversations/{id}` | 删除（级联消息） |
| GET | `/conversations/{id}/messages` | 消息列表（含附件） |
| PUT | `/conversations/{id}/mcp` | 设置 MCP 选择 |
| PUT | `/conversations/{id}/skills` | 设置技能选择 |

## 聊天与文件

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/chat` | 用户 | SSE 流式聊天 |
| POST | `/upload` | 用户 | 上传文件 |
| GET | `/files/{id}` | 用户 | 读取附件 |
| GET | `/endpoints` | 用户 | 可用接口与模型 |
| GET | `/knowledge-bases` | 用户 | 可用知识库（frontend 模式） |
| GET | `/mcp` | 用户 | 可用 MCP（frontend 模式） |
| GET | `/skills` | 用户 | 可用技能 |
| GET | `/quota` | 用户 | Token 限额状态 |

### `POST /api/chat` 请求体

```json
{
  "conversation_id": 1,
  "content": "你好",
  "attachment_ids": [],
  "endpoint_id": null,
  "model": null,
  "web_search": false,
  "knowledge_base_id": null
}
```

响应为 `text/event-stream`，每帧 `data: <json>\n\n`，事件类型见 [功能详解](features.md#sse-事件格式)。

## 站点配置（公开）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/logo`、`/favicon`、`/assistant-avatar` | 站点资源 |
| GET | `/config/site` | 站点标题 / 助手默认名与头像 / favicon |
| GET | `/config/theme` | 主题 |
| GET | `/config/debug` | 调试模式 |
| GET | `/config/sms` | 短信与验证码开关 |
| GET | `/config/wecom` `\| /dingtalk \| /feishu` | 渠道启用状态 |
| GET | `/config/search` | 联网搜索是否可用（用户） |

## 管理后台 `/api/admin`

除 `login` / `me` / `password` 外，默认要求超级管理员（`super`）；部门管理员（`dept`）可访问本部门相关接口。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/login` | 管理员登录 |
| GET | `/admin/me` | 当前管理员 |
| PUT | `/admin/password` | 修改密码 |
| GET | `/admin/access?r=` | 后台随机地址校验 |
| GET | `/admin/stats` | 首页统计 |
| GET/PUT | `/admin/system` `\| /theme \| /debug` | 系统设置 |
| POST/DELETE | `/admin/logo` `\| /favicon \| /assistant-avatar` | 品牌资源 |
| GET/PUT | `/admin/sms` `\| /search` | 短信 / 搜索配置 |
| GET/POST | `/admin/endpoints`，PUT/DELETE `/admin/endpoints/{id}`，GET `/admin/endpoints/usage` | 接口管理 |
| GET/POST/PUT/DELETE | `/admin/knowledge-bases[...]`，POST `/admin/knowledge-bases/test` | 知识库 |
| GET/POST/PUT/DELETE | `/admin/mcp[...]`，POST `/admin/mcp/{id}/test`、`/refresh` | MCP |
| GET/POST/PUT/DELETE | `/admin/skills[...]`，POST `/admin/skills/{id}/test` | 技能 |
| GET/POST/PUT/DELETE | `/admin/wecom-bots`（`?provider=`） | 机器人 |
| GET/PUT | `/admin/wecom` `\| /dingtalk \| /feishu` | 渠道基础配置 |
| GET | `/admin/users`，DELETE `/admin/users/{id}`，PUT `/admin/users/{id}/department`、`/token-limit` | 用户 |
| GET/POST/PUT/DELETE | `/admin/groups[...]` | 用户组 |
| GET/POST/PUT/DELETE | `/admin/agreements[...]` | 协议 |
| GET/POST/PUT/DELETE | `/admin/departments[...]`，PUT `/admin/departments/{id}/admins`，GET `/admin/departments/mine`、`/mine/stats` | 部门 |
| GET/POST/PUT/DELETE | `/admin/admins[...]` | 管理员账号 |
| GET | `/admin/audit-logs`，GET `/admin/audit-logs/export` | 审计日志 / 导出 |
| GET | `/admin/db`，POST `/admin/db/test`、`/switch`、`/backup` | 数据库 |

## 机器人回调

| 方法 | 路径 |
|------|------|
| GET/POST | `/api/wecom/bot/{bot_id}/callback` |
| GET/POST | `/api/dingtalk/bot/{bot_id}/callback` |
| POST | `/api/feishu/bot/{bot_id}/callback` |

## 健康检查

`GET /api/health` → `{"status": "ok"}`。
