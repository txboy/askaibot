# 前端 Chat.vue 与 Admin.vue 子组件化重构方案

> **目标**：把 `frontend/src/views/Chat.vue`（1404 行）与 `frontend/src/views/Admin.vue`（2799 行）全面子组件化，拆出清晰、可维护的组件与组合式函数。
> **安全性**：纯前端重构。不改路由、不改接口、不改后端；以 `npm run build` 作为唯一护栏（无前端测试套件）。路由入口保持 `/` → Chat、`/admin` → Admin。

**技术栈**：Vue 3 `<script setup>` + Vite；已有 `store.js`/`api.js`/`theme.js`，以及 `composables/useConfirm.js`、`components/ConfirmDialog.vue`、`ProfileModal.vue` 等基础设施。

---

## 总体目标

- Admin 每区块一个子组件；Chat 拆成组件 + 共享 composable。
- 两个视图文件都大幅瘦身，组件各自持有状态、模板与专属 scoped CSS。
- 关键约束：
  - **懒加载**：Admin 各区块子组件 `onMounted` 自装载（打开区块才拉数据），替代原「登录后一次性全载」。
  - **Chat 状态共享**：用单例 composable（模块级 reactive）避免各子组件各持一份不互通的 ref。
  - **CSS 类名不变**，仅迁移位置，减少视觉回归。
  - 分阶段执行（A Admin → B Chat → C 收尾），每阶段跑 `npm run build` 再继续。

---

## Part 1：Admin.vue 拆分（`src/views/admin/`）

### 壳：`views/Admin.vue`（保留，路由 `/admin` 不变）
仅保留：
- `isAdmin()` 登录态、`active`、`navItems`（13 项列表）
- **登录表单**（`username`/`password`/`msg`/`loggingIn`/`doLogin`）——登录属鉴权门且体量小，保留在壳
- 侧边栏 `<aside class="admin-side">`（Logo + nav + 退出登录）
- `<main class="admin-main">` + `<component :is="currentSection" />` 切换当前区块
- `logout`、`active` 状态管理、`selectSection(key)` 仅设置 `active`
- 布局/公共类 CSS（`.admin-layout`/`.admin-side`/`.admin-main`/`.nav`/`.content`/`.card`/`.btn` 等）

> 说明：`navItems` 含 `password` 项，且模板中 `active === 'password'` 为 `v-else` 默认分支，故共 **13 个区块组件**。

### 子组件：`src/views/admin/`（13 个）
| 组件 | 对应区块 | 主要职责 |
|---|---|---|
| `AdminDashboard.vue` | dashboard | 统计卡片、刷新；`loadStats`/`loadEndpointsUsage` |
| `AdminUsers.vue` | users | 用户列表、`delUser`；`loadUsers` |
| `AdminEndpoints.vue` | endpoints | 接口增删改；`loadEndpoints`/`save`/`del`/`openCreate`/`openEdit` |
| `AdminSms.vue` | sms | 短信/验证码配置（含防刷 card）；`loadSms`/`saveSms`/`saveCaptcha`/`buildCaptchaBody` |
| `AdminSearch.vue` | search | 联网搜索配置；`loadSearch`/`saveSearch` |
| `AdminMcp.vue` | mcp | MCP 服务增删改测；`loadMcps`/`saveMcp`/`delMcp`/`testMcp`/`refreshMcpTools` |
| `AdminSkill.vue` | skill | 技能包管理（上传/编辑/测试）；`loadSkills`/`onSkillFile`/`uploadSkill`/`runSkillTest`… |
| `AdminKnowledge.vue` | knowledge | 知识库增删改测；`loadKbs`/`saveKb`/`testKb`/`delKb` |
| `AdminWecom.vue` | wecom | 企微集成 + 机器人；`loadWecom`/`saveWecom`/`loadBots('wecom')` |
| `AdminDingtalk.vue` | dingtalk | 钉钉集成 + 机器人；`loadDingtalk`/`saveDingtalk`/`loadBots('dingtalk')` |
| `AdminFeishu.vue` | feishu | 飞书集成 + 机器人；`loadFeishu`/`saveFeishu`/`loadBots('feishu')` |
| `AdminSystem.vue` | system | 站点/主题/调试/后台访问/logo/头像等；`loadSystem`/`saveTheme`/`saveSite`/`uploadLogo`… |
| `AdminPassword.vue` | password(默认) | 修改密码；`changePassword` |

### 状态 / 数据迁移
- 各区块数据相互独立（endpoints/stats/users/kbs/bots/mcps/skills 各归各），无跨区块共享引用。
- 每个子组件 `onMounted` 自装载；`401/管理员` 过期处理保留在壳（通过共享 `store` 判断或子组件 emit → 壳 `logout`）。
- 私有辅助（`buildCaptchaBody`/`resetCaptchaSecrets`/`botModelOptions` 等 comp裸）随区块移动。

### CSS
- 壳保留布局/导航/通用类；各区块专属类随对应子组件迁移，`grep` 确认无悬挂类名。

---

## Part 2：Chat.vue 拆分（组件 + composable）

### 共享逻辑：`composables/useChat.js`（模块级单例 reactive）
持有全部共享 refs 与动作，仿 `useConfirm` 但共享状态：
- 会话：`conversations`/`currentConversation`/`selectConversation`/`newConversation`/`deleteConversation`/`renameConversation`/`loadConversations`
- 发送/流：`messages`/`input`/`streaming`/`errorMsg`/`send`/`scrollToBottom`/`onKeydown`
- 附件：`pendingAttachments`/`uploading`/`fileInputRef`/`pickFiles`/`onFilesSelected`/`removePending`
- 接口/模型：`endpoints`/`selectedEndpointId`/`selectedModel`/`endpointPickerOpen`/`currentSelectionText`/`selectModel`/`loadEndpoints`
- 知识库：`knowledgeBases`/`selectedKnowledgeBaseId`/`kbPickerOpen`/`currentKnowledgeBaseText`/`selectKnowledgeBase`
- MCP：`mcpServers`/`selectedMcpIds`/`mcpPickerOpen`/`parseMcpIds`/`toggleMcp`/`clearMcpSelection`
- 技能：`skills`/`selectedSkillIds`/`skillPickerOpen`/`parseSkillIds`/`toggleSkill`/`clearSkillSelection`
- 杂项：`sidebarOpen`/`profileOpen`/`me`/`avatarSrc`/`assistantName`/`assistantAvatarSrc`/`logout`/`onMounted` 初始化

各子组件 `import { useChat }` 取同一份状态，避免 props 层层穿透。

### 子组件：`src/components/chat/`
| 组件 | 对应模板行 | 职责 |
|---|---|---|
| `ChatSidebar.vue` | 386-423 | aside：Logo/新建对话/会话列表/用户栏 |
| `MessageList.vue` | 436-473 | `.messages`：欢迎页 + 消息渲染（markdown/附件/搜索中/工具中） |
| `ChatComposer.vue` | 475-566 | `.composer`：输入框/发送/联网切换/选择器入口/待传附件 |
| `EndpointPicker.vue` | 569-597 | 接口+模型选择弹窗 |
| `KnowledgeBasePicker.vue` | 599-630 | 知识库选择弹窗 |
| `McpPicker.vue` | 632-654 | MCP 多选弹窗 |
| `SkillPicker.vue` | 656-678 | 技能多选弹窗 |

### 壳：`views/Chat.vue`
- `useChat` 初始化 + 组装上述组件 + `ProfileModal`/`ConfirmDialog` + 整体布局（含移动端 `mobile-bar`）。
- 布局/动画类保留在壳。

### CSS
- 壳保留 `.chat-layout`/`.backdrop`/`.main` 等布局类；`.sidebar`/`.msg`/`.composer`/`.modal-picker`/`.picker-*` 等随组件迁移。

---

## 风险与注意
1. **无前端测试** → 每完成一个区块/组件跑 `npm run build`，最后整体 build + 手动走查（登录、各区块切换、聊天发送、各选择器）。
2. **CSS 迁移易漏** → 迁移后确认无残留类名悬挂；类名保持不变。
3. **Admin 懒加载行为变化**：由「登录一次性全载」变「区块打开时自装载」，预期改进，需走查各区块首开是否正常。
4. **Chat 状态共享**：用单例 composable，避免新组件各自持有一份不互通的 ref。
5. 纯前端重构，**后端及 167 个 pytest 不受影响**。

---

## 分阶段执行
- **阶段 A（Admin）**：建 `src/views/admin/` 与壳 → 先拆 2 个试点（`AdminSystem`/`AdminDashboard`）→ `npm run build` → 依次拆完 13 个 → 整体 build。
- **阶段 B（Chat）**：建 `composables/useChat.js` → 拆 `ChatSidebar`/`MessageList`/`ChatComposer` → 拆 4 个 Picker → 壳瘦身 → 整体 build。
- **阶段 C（收尾）**：最终 `npm run build` + 手动走查主流程；`grep` 确认无悬挂类名/未使用 ref 引入。

## 验证
每阶段：`cd D:\askai\frontend && npm run build` 通过；最终整体 build + 手动走查。
