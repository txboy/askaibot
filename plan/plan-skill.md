# 技能包（Skill）功能 + 沙箱执行

让 askai 支持「技能包」：管理员上传下载好的技能包（含脚本/工具），可全局或按用户分配；用户在会话内勾选启用。启用后注入 SKILL.md 指令，并把声明的工具暴露为可调用函数。技能脚本在沙箱中执行（Docker 优先 + 软沙箱回退，允许联网）。

## 技能包格式（SKILL.md 声明 CLI 命令）

```
skill-pkg.zip
├── SKILL.md        # YAML frontmatter + Markdown 正文（正文注入为系统提示词）
└── tools/...       # 脚本/资源
```

SKILL.md frontmatter 示例：

```yaml
---
name: 代码检查
description: 对代码做静态检查
tools:
  - name: run_lint
    description: 运行 lint
    command: python tools/lint.py   # 包内相对路径；python|node 可运行
---
# 注入给模型的指令正文
```

- **工具参数**：模型生成的 `arguments`(object) 序列化为 JSON 写入命令 **stdin**；命令以 `cwd=技能包目录` 运行，stdout 作为工具结果。
- 工具名命名空间化：`skill__{slug}__{tool}`（避免与 `mcp__`、`web_search` 冲突）。

## 沙箱执行（Docker 优先 + 软沙箱回退，允许联网）

- **Docker 路径**：`docker run --rm -i --cpus 1 --memory 512m --pids-limit 64 -v <data_volume>:/app/data:ro -w /app/data/uploads/skills/{id} <skill_runner_image> sh -c "<command>"`，stdin=JSON；不禁网。
- **软沙箱回退**：检测不到 Docker（本地开发/测试）时用 `subprocess.run(command, cwd=skill_dir, input=json.dumps(args), capture_output=True, timeout=60, env=精简)`，配合 `resource.setrlimit`(CPU/内存/进程数) + `timeout`。
- 由 `skill_sandbox` 配置（`auto`/`docker`/`local`，默认 `auto`）决定；`call_tool` 实现成可注入化便于测试 mock。

## 部署/配置改动

1. **`docker/Dockerfile.skill-runner`**（新）：基于 `python:3.12-slim` + 安装 node；构建为 `askai-skill-runner` 镜像。
2. **`docker/Dockerfile.backend`**：无需安装 docker CLI（后台通过 Python `docker` SDK 调宿主 Docker，见 `requirements.txt` 的 `docker` 依赖）。
3. **`docker/docker-compose.yml`**：backend 挂载 `/var/run/docker.sock`（读写）；新增 `skill-runner` 镜像 build；注入环境变量。
4. **`app/config.py`**：`skill_sandbox`(默认 auto)、`skill_runner_image`(默认 askai-skill-runner)、`skill_data_volume`(默认 app_data)、`skill_data_mount`(默认 /app/data)、资源上限常量。

## 后端功能（backend/）

1. **`app/models.py`**：
   - 新增 `Skill`：id,name,description,dir_path,tools(JSON),scope(global/user),enabled,created_at,updated_at
   - 新增 `SkillAccess`：skill_id,user_id（scope=user 的分配关系）
   - `Conversation` 加 `skill_ids`（逗号分隔，仿 mcp_ids）
   - `WecomBot` 加 `skill_ids`（逗号分隔，仿 mcp_ids）
2. **`app/skills.py`**（新核心模块，仿 mcp.py）：
   - `extract_upload(archive)`：解压 zip/tar.gz，防 zip-slip（校验解压路径均在目标内），返回 dir_path
   - `parse_skill`：解析 SKILL.md frontmatter（name/description/tools），校验 `command` 为包内相对路径
   - `build_openai_tools(skills)` → (tools, mapping)：名 `skill__{slug}__{tool}`
   - `call_tool(skill, tool, args)`：docker/local 执行，stdout 为结果，超时/失败返回错误文本
3. **`app/routers/skills.py`**（新用户路由）：`GET /api/skills` 返回当前用户可用技能（global + 分配给本用户的，含工具元信息）
4. **`app/routers/admin.py`**（仿 MCP CRUD）：`GET/POST(上传zip)/PUT/DELETE /admin/skills` + `POST /admin/skills/{id}/test`；上传→解压→解析→落库
5. **`app/routers/conversations.py`**：新增 `PUT /api/conversations/{id}/skills`
6. **`app/routers/chat.py`**：按 `conversation.skill_ids` 加载技能（校验用户可访问）；①SKILL.md 正文作为 system 消息注入；②`base_tools` 追加 skill 工具；③`skill__*` 分发 `skills.call_tool`
7. **`app/wecom_bot.py::generate_reply`**：按 `bot.skill_ids` 注入技能 system 消息 + skill 工具（并入现有 tools，单轮工具循环 `round_index<1`），分发 `skill__*`
8. **`app/schemas.py`**：`SkillToolOut/SkillOut/SkillUploadResponse`；`ConversationCreate/Out`、`WecomBotCreate/Update/Out` 加 `skill_ids`；`ConversationSkillUpdate`
9. **`app/main.py`**：注册 skills 路由；`_ensure_columns` 迁移 `conversations.skill_ids`、`wecom_bots.skill_ids`（`create_all` 自动建 `skills`/`skill_access` 表）

## 前端功能（frontend/）

1. **`src/api.js`**：`listSkills/uploadSkill/updateSkill/deleteSkill/testSkill/updateConversationSkills`
2. **`src/views/Admin.vue`**：「技能」导航页 —— 列表/上传包/编辑（名称·描述·可见性 global|user·分配用户·启用）/删除/试运行工具
3. **`src/views/Chat.vue`**：会话工具面板加「技能」多选（仿 MCP 选择器，仅列当前用户可用技能），写入 `skill_ids`；`tooling` 状态提示

## 测试

- `backend/tests/test_skills.py`：frontmatter 解析、zip 上传解压（含 zip-slip 拒绝）、工具命名空间映射、`call_tool`（mock docker/local，聚焦软沙箱路径）、会话/机器人技能注入、chat/wecom tool 路由
- 全量 `pytest` 通过；`npm run build` 通过

## 安全

- 解压路径校验（防目录穿越）、限文件大小/数量。
- 命令解析为包内相对路径；sandbox 容器资源受限（CPU/内存/进程数/超时）、技能目录只读挂载。
- 后端容器因挂载 `docker.sock` 具备容器控制权（与后台管理员同等信任级别，因仅管理员能上传技能）。
- 允许联网意味着技能脚本可访问外网，属信任管理员上传的自定义代码。
