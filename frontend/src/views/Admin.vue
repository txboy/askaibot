<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { store } from '../store'
import Logo from '../components/Logo.vue'
import AdminDashboard from './admin/AdminDashboard.vue'
import AdminUsers from './admin/AdminUsers.vue'
import AdminGroups from './admin/AdminGroups.vue'
import AdminAgreements from './admin/AdminAgreements.vue'
import AdminDepartments from './admin/AdminDepartments.vue'
import AdminAdmins from './admin/AdminAdmins.vue'
import AdminAudit from './admin/AdminAudit.vue'
import AdminDeptStats from './admin/AdminDeptStats.vue'
import AdminEndpoints from './admin/AdminEndpoints.vue'
import AdminSms from './admin/AdminSms.vue'
import AdminSearch from './admin/AdminSearch.vue'
import AdminMcp from './admin/AdminMcp.vue'
import AdminSkill from './admin/AdminSkill.vue'
import AdminKnowledge from './admin/AdminKnowledge.vue'
import AdminWecom from './admin/AdminWecom.vue'
import AdminDingtalk from './admin/AdminDingtalk.vue'
import AdminFeishu from './admin/AdminFeishu.vue'
import AdminSystem from './admin/AdminSystem.vue'
import AdminDatabase from './admin/AdminDatabase.vue'
import AdminPassword from './admin/AdminPassword.vue'

const username = ref('')
const password = ref('')
const msg = ref('')
const loggingIn = ref(false)

const active = ref('dashboard')

const isAdmin = () => !!store.adminToken
const isSuper = computed(() => store.adminRole === 'super')

const homeNav = { key: 'dashboard', label: '首页', icon: 'house' }

const superGroups = [
  {
    key: 'org',
    label: '用户管理',
    icon: 'users',
    children: [
      { key: 'users', label: '用户列表', icon: 'user' },
      { key: 'departments', label: '部门管理', icon: 'sitemap' },
      { key: 'admins', label: '管理员', icon: 'user-shield' },
      { key: 'groups', label: '用户组', icon: 'users' },
      { key: 'password', label: '修改密码', icon: 'lock' },
    ],
  },
  {
    key: 'capability',
    label: '工具接入',
    icon: 'wand-magic-sparkles',
    children: [
      { key: 'endpoints', label: '接口设置', icon: 'plug' },
      { key: 'sms', label: '短信接口', icon: 'sms' },
      { key: 'search', label: '联网搜索', icon: 'magnifying-glass' },
      { key: 'mcp', label: 'MCP 工具', icon: 'server' },
      { key: 'skill', label: '技能包', icon: 'wand-magic-sparkles' },
      { key: 'knowledge', label: '知识库', icon: 'book' },
    ],
  },
  {
    key: 'channel',
    label: '渠道接入',
    icon: 'share-nodes',
    children: [
      { key: 'wecom', label: '企微设置', icon: 'comment' },
      { key: 'dingtalk', label: '钉钉设置', icon: 'robot' },
      { key: 'feishu', label: '飞书设置', icon: 'comments' },
    ],
  },
  {
    key: 'system',
    label: '系统管理',
    icon: 'gear',
    children: [
      { key: 'system', label: '系统设置', icon: 'sliders' },
      { key: 'database', label: '数据库', icon: 'database' },
      { key: 'audit', label: '审计日志', icon: 'file-lines' },
      { key: 'agreement', label: '协议管理', icon: 'file-signature' },
    ],
  },
]

const deptNav = [
  { key: 'users', label: '本部门用户', icon: 'user' },
  { key: 'dept-stats', label: '本部门用量', icon: 'chart-line' },
  { key: 'password', label: '修改密码', icon: 'lock' },
]

const isDept = computed(() => store.adminRole === 'dept')

const openGroups = ref([])

function toggleGroup(key) {
  openGroups.value = openGroups.value.includes(key) ? [] : [key]
}

function groupOf(key) {
  return superGroups.find((g) => g.children.some((c) => c.key === key))
}

const sectionMap = {
  dashboard: AdminDashboard,
  users: AdminUsers,
  departments: AdminDepartments,
  admins: AdminAdmins,
  groups: AdminGroups,
  agreement: AdminAgreements,
  endpoints: AdminEndpoints,
  sms: AdminSms,
  search: AdminSearch,
  mcp: AdminMcp,
  skill: AdminSkill,
  knowledge: AdminKnowledge,
  wecom: AdminWecom,
  dingtalk: AdminDingtalk,
  feishu: AdminFeishu,
  system: AdminSystem,
  database: AdminDatabase,
  audit: AdminAudit,
  'dept-stats': AdminDeptStats,
  password: AdminPassword,
}

const currentSection = computed(() => sectionMap[active.value] || AdminPassword)

function selectSection(key) {
  active.value = key
  const g = groupOf(key)
  if (g) {
    openGroups.value = [g.key]
  }
}

async function loadMe() {
  try {
    const me = await api.adminMe()
    store.setAdminRole(me.role)
  } catch (e) {
    store.setAdminRole('')
  }
}

onMounted(() => {
  if (store.adminToken) loadMe()
})

async function doLogin() {
  if (!username.value || !password.value) return (msg.value = '请输入用户名和密码')
  msg.value = ''
  loggingIn.value = true
  try {
    const r = await api.adminLogin(username.value, password.value)
    store.setAdminToken(r.token)
    await loadMe()
    active.value = 'dashboard'
  } catch (e) {
    msg.value = e.message
  } finally {
    loggingIn.value = false
  }
}

function logout() {
  store.logoutAdmin()
}
</script>

<template>
  <div class="admin-layout">
    <div v-if="!isAdmin()" class="login-wrap">
      <div class="login-card">
        <h2>管理后台登录</h2>
        <input v-model="username" class="input" placeholder="用户名（默认 admin）" @keyup.enter="doLogin" />
        <input v-model="password" type="password" class="input" placeholder="密码（默认 admin123）" @keyup.enter="doLogin" />
        <button class="btn full" :disabled="loggingIn" @click="doLogin">{{ loggingIn ? '登录中…' : '登录' }}</button>
        <p v-if="msg" class="msg">{{ msg }}</p>
        <a class="back" href="/">← 返回聊天</a>
      </div>
    </div>

    <template v-else>
      <aside class="admin-side">
        <div class="side-head"><Logo class="side-logo" /></div>
        <nav class="nav">
          <template v-if="isDept">
            <button
              v-for="n in deptNav"
              :key="n.key"
              class="nav-item"
              :class="{ active: active === n.key }"
              @click="selectSection(n.key)"
            >
              <font-awesome-icon :icon="n.icon" class="nav-ic" />
              {{ n.label }}
            </button>
          </template>
          <template v-else>
            <button
              class="nav-item"
              :class="{ active: active === homeNav.key }"
              @click="selectSection(homeNav.key)"
            >
              <font-awesome-icon :icon="homeNav.icon" class="nav-ic" />
              {{ homeNav.label }}
            </button>
            <div v-for="g in superGroups" :key="g.key" class="nav-group">
              <button
                class="nav-group-head"
                :class="{ open: openGroups.includes(g.key) }"
                @click="toggleGroup(g.key)"
              >
                <font-awesome-icon :icon="g.icon" class="nav-ic" />
                <span class="group-label">{{ g.label }}</span>
                <font-awesome-icon icon="chevron-down" class="chev" />
              </button>
              <template v-if="openGroups.includes(g.key)">
                <button
                  v-for="c in g.children"
                  :key="c.key"
                  class="nav-item sub"
                  :class="{ active: active === c.key }"
                  @click="selectSection(c.key)"
                >
                  <font-awesome-icon :icon="c.icon" class="nav-ic" />
                  {{ c.label }}
                </button>
              </template>
            </div>
          </template>
        </nav>
        <div class="side-foot">
          <button class="nav-item" @click="logout">退出登录</button>
        </div>
      </aside>

      <main class="admin-main">
        <component :is="currentSection" />
      </main>
    </template>
  </div>
</template>

<style>
/* Global admin console styles shared by all section components. */
.admin-layout {
  display: flex;
  height: 100%;
  background: var(--bg);
}

.login-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow);
}

.login-card h2 {
  text-align: center;
  margin-bottom: 8px;
}

.back {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  text-decoration: none;
}

.admin-side {
  width: 220px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 18px 12px;
}

.side-head {
  font-size: 16px;
  font-weight: 600;
  padding: 4px 4px 16px;
  color: var(--text);
}

.side-logo {
  max-width: 100%;
  height: auto;
}

.nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding-top: 6px;
}

.nav-item {
  text-align: left;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 15px;
  transition: background 0.15s, color 0.15s;
}

.nav-item:hover {
  background: var(--primary-soft);
  color: var(--text);
}

.nav-item.active {
  background: var(--primary);
  color: #fff;
}

.nav-ic {
  width: 14px;
  margin-right: 8px;
  text-align: center;
}

.nav-item.sub {
  padding-left: 32px;
  font-size: 14px;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.nav-group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  text-align: left;
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  font-weight: 600;
  font-size: 15px;
  transition: background 0.15s, color 0.15s;
}

.nav-group-head:hover {
  background: var(--primary-soft);
  color: var(--text);
}

.nav-group-head .group-label {
  flex: 1;
}

.nav-group-head .chev {
  font-size: 11px;
  transition: transform 0.2s ease;
  color: var(--text-muted);
}

.nav-group-head.open .chev {
  transform: rotate(180deg);
}

.side-foot {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

.admin-main {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
}

.content {
  width: 100%;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.content h2 {
  font-size: 20px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  margin: 26px 0 12px;
}

.theme-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
}

.theme-options {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.theme-radio {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.theme-radio:hover {
  border-color: var(--primary);
}

.theme-radio.selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.theme-radio input {
  display: none;
}

.theme-swatch {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid var(--border);
  position: relative;
  flex-shrink: 0;
}

.theme-swatch::after {
  content: '';
  position: absolute;
  inset: 0;
  margin: auto;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.theme-swatch.swatch-warm {
  background: #fbf6ef;
}

.theme-swatch.swatch-warm::after {
  background: #e0804a;
}

.theme-swatch.swatch-cool {
  background: #eef2f7;
}

.theme-swatch.swatch-cool::after {
  background: #4a7dbd;
}

.theme-swatch.swatch-tech {
  background: #0d1117;
}

.theme-swatch.swatch-tech::after {
  background: #00d4a8;
}

.theme-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 14px;
}

.debug-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  text-align: center;
}

.stat-num {
  font-size: 30px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

.card-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 420px;
}

.card-form label,
.modal label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 13px;
  color: var(--text-muted);
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 14px;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.table th,
.table td {
  border-bottom: 1px solid var(--border);
  padding: 10px 8px;
  text-align: left;
}

.table th {
  color: var(--text-muted);
  font-weight: 500;
}

.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
}

.del {
  color: var(--danger);
}

.ops {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-edit {
  background: var(--primary);
}

.btn-edit:hover {
  background: var(--primary-hover);
}

.btn-test {
  background: #46a869;
}

.btn-test:hover {
  background: #3c9a5c;
}

.btn-del {
  background: var(--danger);
}

.btn-del:hover {
  background: #c94440;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 24px;
}

.wecom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.wecom-grid label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 13px;
  color: var(--text-muted);
}

.sm-label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.row-btn {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sms-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.sms-grid label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 13px;
  color: var(--text-muted);
}

.form-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-2 label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 13px;
  color: var(--text-muted);
}

.kb-checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 0;
}

.mcp-tools {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-soft);
}

.tools-list {
  margin: 6px 0 8px;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 180px;
  overflow-y: auto;
}

.tools-list li code {
  margin-right: 8px;
  color: var(--primary);
}

.skill-upload {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-soft);
}

.skill-upload input[type='file'] {
  font-size: 13px;
}

.skill-output {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-soft);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow-y: auto;
  font-size: 13px;
}

.hint {
  font-size: 13px;
  color: var(--text-muted);
}

.hint-danger {
  color: var(--danger);
}

.logo-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.logo-preview {
  width: 200px;
  height: 120px;
  border: 1px dashed var(--border);
  border-radius: 10px;
  background: var(--bg-sidebar);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.logo-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.favicon-preview {
  width: 72px;
  height: 72px;
}

.logo-empty {
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  padding: 0 12px;
}

.logo-ops {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.file-btn {
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.file-btn input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.msg {
  width: 100%;
  color: var(--danger);
  font-size: 13px;
  margin: 4px 0 10px;
}

.modal {
  background: var(--surface);
  border-radius: 12px;
  padding: 24px;
  width: 460px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal h3 {
  margin-bottom: 4px;
}

.check {
  flex-direction: row !important;
  align-items: center;
  gap: 8px !important;
}

.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.kb-test {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.kb-test-result {
  flex: 1;
  font-size: 13px;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}

.full {
  width: 100%;
}
</style>
