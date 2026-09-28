# 后端 MVC 重构实施方案

> **目标**：将后端从「单文件 models + routers 混排」重构为 MVC 分层——`models` 按表分包、`controllers` 分后台(admin)/前端(frontend)/回调(webhook)、业务逻辑抽取到 `services`。
> **安全性**：本次为纯结构重构，不改任何路由 URL、不改行为；以现有 167 个 pytest 用例作为回归护栏，每个阶段跑通后再进入下一阶段。

**技术栈**：FastAPI + SQLAlchemy 2.0 + Pydantic v2，绝对导入（`from app import models`）。

---

## 目标目录结构

```
backend/app/
  main.py                      # 改为从 controllers 导入
  config.py / database.py / schemas.py / auth.py / common.py / security.py / filetools.py   # 保留在根（跨切面工具）
  models/                      # 新增：按表分包
    __init__.py                # 聚合导出全部模型 + Base，保证 `from app import models` 兼容
    user.py conversation.py message.py setting.py knowledge_base.py
    wecom_bot.py attachment.py admin.py mcp_server.py api_endpoint.py skill.py
  services/                    # 新增：抽取业务逻辑
    __init__.py kb.py mcp.py skills.py sms.py search.py
    wecom_bot.py dingtalk_bot.py feishu_bot.py wecom_crypto.py feishu_crypto.py captcha.py
  controllers/                 # 新增：MVC 控制器
    admin/                     # 后台管理（拆 /admin 单体为多个域）
      __init__.py auth.py system.py sms.py search.py endpoints.py knowledge_bases.py
      mcp.py skills.py wecom_bots.py integrations.py users.py
    frontend/                  # 前端用户接口
      __init__.py auth.py chat.py conversations.py endpoints.py mcp.py skills.py uploads.py
    webhook/                   # 企微/钉钉/飞书公开回调
      __init__.py wecom_bot.py dingtalk_bot.py feishu_bot.py
```

删除：`app/models.py`、`app/routers/`（含未注册的孤儿 `brand.py`）。

---

## 阶段 0：基线

```
cd D:\askai\backend && python -m pytest -q   # 预期 167 passed
```

---

## 阶段 1：models 按表分包（低风险，零导入改动）

**步骤 1**：建 `app/models/__init__.py`，聚合导出并保留 `Base`：
```python
from ..database import Base
from .user import User
from .conversation import Conversation
from .message import Message
from .setting import Setting
from .knowledge_base import KnowledgeBase
from .wecom_bot import WecomBot
from .attachment import Attachment
from .admin import Admin
from .mcp_server import McpServer
from .api_endpoint import ApiEndpoint
from .skill import Skill, SkillAccess
__all__ = ["Base","User","Conversation","Message","Setting","KnowledgeBase","WecomBot","Attachment","Admin","McpServer","ApiEndpoint","Skill","SkillAccess"]
```
**步骤 2**：把 `app/models.py` 中 12 张表的类按上表分别移到 `app/models/<表>.py`，每个文件顶部 `from ..database import Base`（或 `from app.database import Base`）。`skill.py` 同时放 `Skill` 与 `SkillAccess`。
**步骤 3**：删除 `app/models.py`。
**步骤 4**：验证 `python -m pytest -q` → **167 passed**。

> 关键：`app/models` 是包后，`from .. import models` / `from app import models` / `models.Setting` 全部照常工作，`Base.metadata.create_all` 在 main.py 导入控制器时已注册全部表，无需改动其他文件。

---

## 阶段 2：抽取 services 层（移动领域逻辑）

**步骤 1**：建 `app/services/__init__.py`（空）。
**步骤 2**：把 `kb.py`、`mcp.py`、`skills.py`、`sms.py`、`search.py`、`wecom_bot.py`、`dingtalk_bot.py`、`feishu_bot.py`、`wecom_crypto.py`、`feishu_crypto.py`、`captcha.py` 移入 `app/services/`，并把内部相对导入改为绝对导入：
- `from . import models` → `from app import models`
- `from .config import config` → `from app.config import config`
- `from .common import ...` → `from app.common import ...`
- `from .kb import ...` / `from . import mcp` 等（services 内部互相引用）→ `from app.services import kb` / `from app.services import mcp`
**步骤 3**：更新所有引用（此时 controllers 仍位于 `app/routers/`）：
- `routers/*.py`：`from .. import kb` → `from ..services import kb`；`from ..kb import ...` → `from ..services.kb import ...`；`from .. import captcha as captcha_mod` → `from ..services import captcha as captcha_mod`；`from ..sms import send_sms` → `from ..services.sms import send_sms`；`from .. import dingtalk_bot`/`wecom_bot`/`feishu_bot`/`wecom_crypto`/`feishu_crypto`/`mcp`/`skills` → `from ..services import ...`
- **测试**：`app.kb`→`app.services.kb`、`app.captcha`→`app.services.captcha`、`app.mcp`→`app.services.mcp`、`app.skills`→`app.services.skills`、`app.search`→`app.services.search`、`app.wecom_bot`→`app.services.wecom_bot`、`app.dingtalk_bot`→`app.services.dingtalk_bot`、`app.feishu_bot`→`app.services.feishu_bot`、`app.wecom_crypto`→`app.services.wecom_crypto`、`app.feishu_crypto`→`app.services.feishu_crypto`
**步骤 4**：`python -m pytest -q` → **167 passed**。

---

## 阶段 3：controllers 迁移（前端 + 回调，机械搬运）

**步骤 1**：建 `app/controllers/__init__.py`、`app/controllers/frontend/__init__.py`、`app/controllers/webhook/__init__.py`（空）。
**步骤 2**：搬运到 `controllers/frontend/`：`auth.py`、`chat.py`、`conversations.py`、`endpoints.py`、`mcp.py`、`skills.py`、`uploads.py`（保留各自 `APIRouter` 前缀/tags 不变）。
**步骤 3**：搬运到 `controllers/webhook/`：`wecom_bot.py`、`dingtalk_bot.py`、`feishu_bot.py`。
**步骤 4**：把每个新文件内的相对导入改写为绝对导入，例如 `frontend/auth.py`：
```python
from app import models, schemas
from app.services import captcha as captcha_mod
from app.auth import create_token, get_current_user
from app.common import get_setting
from app.config import config
from app.database import get_db
from app.services.sms import send_sms   # 原来在函数内 `from ..sms import send_sms`
```
（其余文件 `from app.services import mcp/skills/kb/search/dingtalk_bot/feishu_bot/wecom_bot/wecom_crypto/feishu_crypto`，`from app.common import ...`，`from app.filetools import ...`）
**步骤 5**：`main.py` 改为：
```python
from .controllers.frontend import (
    auth, chat, conversations, endpoints, mcp, skills, uploads,
)
from .controllers.webhook import wecom_bot, dingtalk_bot, feishu_bot
```
并把 `include_router` 中对应改成 `endpoints.router`/`mcp.router`/`skills.router` 等（前缀、路由路径、`prefix="/api"` 全部不变）。
**步骤 6**：更新测试导入：`app.routers.auth`→`app.controllers.frontend.auth`、`app.routers.chat`→`app.controllers.frontend.chat`、`app.routers.endpoints`→`app.controllers.frontend.endpoints`、`app.routers.conversations`→`app.controllers.frontend.conversations`、`app.routers.uploads`→`app.controllers.frontend.uploads`、`app.routers.wecom_bot/dingtalk_bot/feishu_bot`→`app.controllers.webhook.*`。
**步骤 7**：`python -m pytest -q` → **167 passed**。

---

## 阶段 4：admin 单体拆分为域控制器

**步骤 1**：建 `app/controllers/admin/` 目录，按域拆分（每个文件一个 `APIRouter()`，无前缀）：
- `auth.py`：`admin_login`
- `system.py`：`stats`、`get_system`/`update_system`、`admin_get_theme`/`admin_save_theme`、`admin_get_debug`/`admin_save_debug`、`admin_access`、`upload_favicon`/`delete_favicon`、`upload_assistant_avatar`/`delete_assistant_avatar`、`logo_status`/`upload_logo`/`delete_logo`、`change_password`
- `sms.py`：`get_sms`/`update_sms`
- `search.py`：`get_search`/`update_search`
- `endpoints.py`：`list_endpoints`/`create_endpoint`/`update_endpoint`/`delete_endpoint`/`endpoints_usage`
- `knowledge_bases.py`：`list_knowledge_bases`/`create_knowledge_base`/`update_knowledge_base`/`delete_knowledge_base`/`test_knowledge_base`
- `mcp.py`：`list_mcp_servers`/`create_mcp_server`/`update_mcp_server`/`delete_mcp_server`/`test_mcp_server`/`refresh_mcp_server`
- `skills.py`：`list_skills`/`create_skill`/`update_skill`/`delete_skill`/`test_skill`
- `wecom_bots.py`：`list_wecom_bots`/`create_wecom_bot`/`update_wecom_bot`/`delete_wecom_bot`
- `integrations.py`：`get_wecom`/`update_wecom`/`get_dingtalk`/`update_dingtalk`/`get_feishu`/`update_feishu`
- `users.py`：`list_users`/`delete_user`
- 私有辅助函数（`_endpoint_out` 等）随附着域移动。

**步骤 2**：重构导入为绝对导入：`from app import models, schemas`、`from app.services import mcp as mcp_core, skills as skill_core`、`from app.auth import create_admin_token, get_current_admin`、`from app.common import get_setting, mask_key`、`from app.config import config`、`from app.database import get_db`、`from app.security import hash_password, verify_password`。

**步骤 3**：`admin/__init__.py` 聚合 + 兼容导出：
```python
from fastapi import APIRouter
from app import models, schemas
from app.services import mcp as mcp_core          # 供 test_mcp.py 的 admin_mod.mcp_core 引用
from . import auth, system, sms, search, endpoints, knowledge_bases, mcp, skills, wecom_bots, integrations, users
router = APIRouter(prefix="/admin", tags=["admin"])
for m in (auth, system, sms, search, endpoints, knowledge_bases, mcp, skills, wecom_bots, integrations, users):
    router.include_router(m.router)
# re-export each module's `__all__` route functions for backward-compat with tests
from .auth import *; from .system import *; from .sms import *; from .search import *
from .endpoints import *; from .knowledge_bases import *; from .mcp import *
from .skills import *; from .wecom_bots import *; from .integrations import *; from .users import *
```
每个域模块定义 `__all__ = ["get_sms", "update_sms", ...]`（仅列路由处理函数，不含 `router`），避免 `import *` 冲突。

**步骤 4**：`main.py` 加 `from .controllers.admin import router as admin_router`，把原来的 `admin.router` include 改为 `admin_router`（`/api` 前缀不变，最终仍是 `/api/admin/...`）。

**步骤 5**：更新测试导入：`app.routers.admin`→`app.controllers.admin`；`from app.routers.admin import admin_access`→`from app.controllers.admin import admin_access`。

**步骤 6**：`python -m pytest -q` → **167 passed**。

---

## 阶段 5：清理与最终验证

- 删除 `app/routers/` 整个目录（含孤儿 `brand.py`；`/logo` 功能已由 `uploads.py`/`admin` 提供）。
- `grep -rn "app.routers\|from \.routers\|from \.\.routers" app tests` 确认无残留。
- `cd D:\askai\backend && python -m pytest -q` → **167 passed**。
- `cd D:\askai\frontend && npm run build` → 通过（前端 URL 未变，纯后端重构不影响）。

---

## 风险与注意

1. **迁移顺序**：严格按阶段 1→2→3→4，每阶段跑全量 pytest 确认 167 通过，避免叠加错误难定位。
2. **行政合并**：`admin/__init__.py` 的 `import *` 依赖每个域模块的 `__all__`；务必排除 `router`，避免聚合 `router` 被覆盖。
3. **测试兼容**：刻意让 `app.controllers.admin` 聚合模块保留旧 `admin.py` 的 `models`/`mcp_core`/`schemas` 名称，使 `test_admin_access.py`/`test_mcp.py` 的 `admin_mod.models`、`admin_mod.mcp_core` 仍可用。
4. **绝对导入**：新 controller/service 统一用 `from app import ...` 绝对导入，减少 `...` 多级相对导入的出错率。
