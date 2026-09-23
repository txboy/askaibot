<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { store } from '../store'
import { applyTheme } from '../theme'
import Logo from '../components/Logo.vue'

const username = ref('')
const password = ref('')
const msg = ref('')
const loggingIn = ref(false)

const active = ref('dashboard')
const navItems = [
  { key: 'dashboard', label: '首页' },
  { key: 'users', label: '用户列表' },
  { key: 'endpoints', label: '接口设置' },
  { key: 'sms', label: '短信接口' },
  { key: 'search', label: '联网搜索' },
  { key: 'knowledge', label: '知识库' },
  { key: 'wecom', label: '企微设置' },
  { key: 'wecom-bot', label: '企微机器人' },
  { key: 'logo', label: 'Logo设置' },
  { key: 'system', label: '系统设置' },
  { key: 'password', label: '修改密码' },
]

const stats = ref(null)
const users = ref([])
const endpointsUsage = ref([])

const endpoints = ref([])
const errorMsg = ref('')
const editing = ref(null)

const wecomCorpId = ref('')
const wecomSecret = ref('')
const wecomAgentId = ref('')
const wecomRedirect = ref('')
const wecomSecretSet = ref(false)
const wecomMsg = ref('')
const savingWecom = ref(false)

const logoFile = ref(null)
const logoPreview = ref('')
const logoSet = ref(false)
const logoMsg = ref('')
const savingLogo = ref(false)

const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const pwdMsg = ref('')
const savingPwd = ref(false)

const theme = ref('warm')
const themeMsg = ref('')
const savingTheme = ref(false)
const themeOptions = [
  { value: 'warm', label: '暖色调' },
  { value: 'cool', label: '冷色调' },
  { value: 'tech', label: '科技感' },
]

const debugMode = ref(false)
const debugMsg = ref('')
const savingDebug = ref(false)

const siteTitle = ref('')
const siteMsg = ref('')
const savingSite = ref(false)

const faviconFile = ref(null)
const faviconPreview = ref('')
const faviconSet = ref(false)
const faviconMsg = ref('')
const savingFavicon = ref(false)

const assistantAvatarFile = ref(null)
const assistantAvatarPreview = ref('')
const assistantAvatarSet = ref(false)
const assistantAvatarMsg = ref('')
const savingAssistantAvatar = ref(false)

const adminEnabled = ref(false)
const adminSecret = ref('')
const adminMsg = ref('')
const savingAdmin = ref(false)
const adminUrl = computed(() => window.location.origin + '/admin?r=' + adminSecret.value)

const assistantName = ref('')
const assistantMsg = ref('')
const savingAssistant = ref(false)

const smsProvider = ref('')
const smsAccessKeyId = ref('')
const smsSecret = ref('')
const smsSignName = ref('')
const smsTemplateCode = ref('')
const smsRegion = ref('')
const smsSdkAppId = ref('')
const smsSecretSet = ref(false)
const smsMsg = ref('')
const savingSms = ref(false)
const smsProviders = [
  { value: '', label: '不启用' },
  { value: 'aliyun', label: '阿里云' },
  { value: 'tencent', label: '腾讯云' },
]

const searchProvider = ref('')
const searchApiKey = ref('')
const searchBaseUrl = ref('')
const searchAuto = ref(false)
const searchApiKeySet = ref(false)
const searchMsg = ref('')
const savingSearch = ref(false)
const searchProviders = [
  { value: '', label: '不启用' },
  { value: 'tavily', label: 'Tavily' },
  { value: 'bing', label: 'Bing Web Search' },
  { value: 'searxng', label: 'SearXNG（自托管）' },
  { value: 'duckduckgo', label: 'DuckDuckGo' },
]

const kbs = ref([])
const kbMsg = ref('')
const savingKb = ref(false)
const editingKb = ref(null)

const bots = ref([])
const botMsg = ref('')
const savingBot = ref(false)
const editingBot = ref(null)

const isAdmin = () => !!store.adminToken

async function doLogin() {
  if (!username.value || !password.value) return (msg.value = '请输入用户名和密码')
  msg.value = ''
  loggingIn.value = true
  try {
    const r = await api.adminLogin(username.value, password.value)
    store.setAdminToken(r.token)
    active.value = 'dashboard'
    await load()
  } catch (e) {
    msg.value = e.message
  } finally {
    loggingIn.value = false
  }
}

async function load() {
  try {
    await Promise.all([loadEndpoints(), loadWecom(), loadLogo(), loadStats(), loadUsers(), loadEndpointsUsage(), loadTheme(), loadDebug(), loadSms(), loadSystem(), loadKbs(), loadBots()])
  } catch (e) {
    if (String(e.message).includes('401') || String(e.message).includes('管理员')) {
      logout()
    } else {
      errorMsg.value = e.message
    }
  }
}

async function selectSection(key) {
  active.value = key
  try {
    if (key === 'dashboard') { await loadStats(); await loadEndpointsUsage(); await loadTheme(); await loadDebug() }
    else if (key === 'users') await loadUsers()
    else if (key === 'endpoints') await loadEndpoints()
    else if (key === 'sms') await loadSms()
    else if (key === 'search') await loadSearch()
    else if (key === 'knowledge') await loadKbs()
    else if (key === 'wecom') await loadWecom()
    else if (key === 'wecom-bot') await loadBots()
    else if (key === 'logo') await loadLogo()
    else if (key === 'system') await loadSystem()
  } catch (e) {
    if (String(e.message).includes('401') || String(e.message).includes('管理员')) {
      logout()
    }
  }
}

async function loadEndpoints() {
  endpoints.value = await api.adminEndpoints()
}

async function loadStats() {
  stats.value = await api.adminStats()
}

async function loadEndpointsUsage() {
  endpointsUsage.value = await api.adminEndpointsUsage()
}

async function loadTheme() {
  try {
    const r = await api.adminGetTheme()
    theme.value = r.theme
    applyTheme(r.theme)
  } catch {}
}

async function saveTheme() {
  savingTheme.value = true
  themeMsg.value = ''
  try {
    const r = await api.adminSaveTheme(theme.value)
    theme.value = r.theme
    applyTheme(r.theme)
    themeMsg.value = '已保存'
  } catch (e) {
    themeMsg.value = e.message
  } finally {
    savingTheme.value = false
  }
}

async function loadDebug() {
  try {
    const r = await api.adminGetDebug()
    debugMode.value = !!r.debug_mode
  } catch {}
}

async function toggleDebug() {
  savingDebug.value = true
  debugMsg.value = ''
  try {
    const r = await api.adminSaveDebug(debugMode.value)
    debugMode.value = !!r.debug_mode
    debugMsg.value = '已保存'
  } catch (e) {
    debugMsg.value = e.message
  } finally {
    savingDebug.value = false
  }
}

async function loadSystem() {
  try {
    const r = await api.adminGetSystem()
    siteTitle.value = r.site_title
    faviconSet.value = r.favicon_set
    faviconPreview.value = r.favicon_set ? '/api/favicon?t=' + Date.now() : ''
    adminEnabled.value = r.admin_secret_enabled
    adminSecret.value = r.admin_secret || ''
    assistantName.value = r.assistant_name || 'askai'
    assistantAvatarSet.value = r.assistant_avatar_set
    assistantAvatarPreview.value = r.assistant_avatar_set ? '/api/assistant-avatar?t=' + Date.now() : ''
    siteMsg.value = ''
    faviconMsg.value = ''
    adminMsg.value = ''
    assistantMsg.value = ''
    assistantAvatarMsg.value = ''
  } catch {
    siteMsg.value = '加载系统设置失败'
  }
}

async function saveAssistantName() {
  savingAssistant.value = true
  assistantMsg.value = ''
  try {
    const r = await api.adminSaveSystem({ assistant_name: assistantName.value })
    assistantName.value = r.assistant_name || 'askai'
    assistantMsg.value = '已保存'
  } catch (e) {
    assistantMsg.value = e.message
  } finally {
    savingAssistant.value = false
  }
}

async function saveSite() {
  savingSite.value = true
  siteMsg.value = ''
  try {
    const r = await api.adminSaveSystem({ site_title: siteTitle.value })
    siteTitle.value = r.site_title
    document.title = siteTitle.value || document.title
    siteMsg.value = '已保存'
  } catch (e) {
    siteMsg.value = e.message
  } finally {
    savingSite.value = false
  }
}

function generateAdminSecret() {
  adminSecret.value = Array.from(crypto.getRandomValues(new Uint8Array(12)))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

async function saveAdminSecret() {
  savingAdmin.value = true
  adminMsg.value = ''
  try {
    const r = await api.adminSaveSystem({
      admin_secret_enabled: adminEnabled.value,
      admin_secret: adminSecret.value,
    })
    adminEnabled.value = r.admin_secret_enabled
    adminSecret.value = r.admin_secret || ''
    adminMsg.value = '已保存'
  } catch (e) {
    adminMsg.value = e.message
  } finally {
    savingAdmin.value = false
  }
}

function onFaviconFile(e) {
  const f = e.target.files[0]
  if (!f) return
  faviconFile.value = f
  faviconPreview.value = URL.createObjectURL(f)
  faviconMsg.value = ''
}

async function uploadFavicon() {
  if (!faviconFile.value) return (faviconMsg.value = '请选择图片文件')
  savingFavicon.value = true
  faviconMsg.value = ''
  try {
    const r = await api.adminUploadFavicon(faviconFile.value)
    faviconSet.value = r.favicon_set
    const link = document.querySelector("link[rel~='icon']")
    if (link && faviconSet.value) link.href = '/api/favicon?t=' + Date.now()
    faviconMsg.value = 'Favicon 已保存'
    await loadSystem()
  } catch (e) {
    faviconMsg.value = e.message
  } finally {
    savingFavicon.value = false
  }
}

async function resetFavicon() {
  if (!confirm('恢复默认图标（删除自定义 favicon）？')) return
  try {
    await api.adminDeleteFavicon()
    faviconFile.value = null
    faviconSet.value = false
    faviconPreview.value = ''
    const link = document.querySelector("link[rel~='icon']")
    if (link) link.href = '/favicon.svg'
    faviconMsg.value = '已恢复默认 favicon'
  } catch (e) {
    faviconMsg.value = e.message
  }
}

function onAssistantAvatarFile(e) {
  const f = e.target.files[0]
  if (!f) return
  assistantAvatarFile.value = f
  assistantAvatarPreview.value = URL.createObjectURL(f)
  assistantAvatarMsg.value = ''
}

async function uploadAssistantAvatar() {
  if (!assistantAvatarFile.value) return (assistantAvatarMsg.value = '请选择图片文件')
  savingAssistantAvatar.value = true
  assistantAvatarMsg.value = ''
  try {
    const r = await api.adminUploadAssistantAvatar(assistantAvatarFile.value)
    assistantAvatarSet.value = r.assistant_avatar_set
    assistantAvatarMsg.value = '助手默认头像已保存'
    await loadSystem()
  } catch (e) {
    assistantAvatarMsg.value = e.message
  } finally {
    savingAssistantAvatar.value = false
  }
}

async function resetAssistantAvatar() {
  if (!confirm('恢复默认（删除助手默认头像）？')) return
  try {
    await api.adminDeleteAssistantAvatar()
    assistantAvatarFile.value = null
    assistantAvatarSet.value = false
    assistantAvatarPreview.value = ''
    assistantAvatarMsg.value = '已恢复默认'
  } catch (e) {
    assistantAvatarMsg.value = e.message
  }
}

async function loadSms() {
  try {
    const r = await api.adminGetSms()
    smsProvider.value = r.provider
    smsAccessKeyId.value = r.access_key_id
    smsSignName.value = r.sign_name
    smsTemplateCode.value = r.template_code
    smsRegion.value = r.region
    smsSdkAppId.value = r.sdk_app_id
    smsSecretSet.value = r.secret_set
    smsSecret.value = ''
    smsMsg.value = ''
  } catch (e) {
    smsMsg.value = '加载短信配置失败'
  }
}

async function saveSms() {
  savingSms.value = true
  smsMsg.value = ''
  try {
    const body = {
      provider: smsProvider.value,
      access_key_id: smsAccessKeyId.value,
      sign_name: smsSignName.value,
      template_code: smsTemplateCode.value,
      region: smsRegion.value,
      sdk_app_id: smsSdkAppId.value,
    }
    if (smsSecret.value) body.secret = smsSecret.value
    const r = await api.adminSaveSms(body)
    smsSecret.value = ''
    smsSecretSet.value = r.secret_set
    smsMsg.value = '已保存'
  } catch (e) {
    smsMsg.value = e.message
  } finally {
    savingSms.value = false
  }
}

async function loadSearch() {
  try {
    const r = await api.adminGetSearch()
    searchProvider.value = r.provider
    searchBaseUrl.value = r.base_url || ''
    searchAuto.value = !!r.auto
    searchApiKeySet.value = r.api_key_set
    searchApiKey.value = ''
    searchMsg.value = ''
  } catch (e) {
    searchMsg.value = '加载联网搜索配置失败'
  }
}

async function saveSearch() {
  savingSearch.value = true
  searchMsg.value = ''
  try {
    const body = {
      provider: searchProvider.value,
      base_url: searchBaseUrl.value,
      auto: searchAuto.value,
    }
    if (searchApiKey.value) body.api_key = searchApiKey.value
    const r = await api.adminSaveSearch(body)
    searchApiKey.value = ''
    searchApiKeySet.value = r.api_key_set
    searchMsg.value = '已保存'
  } catch (e) {
    searchMsg.value = e.message
  } finally {
    savingSearch.value = false
  }
}

async function loadUsers() {
  users.value = await api.adminUsers()
}

async function loadKbs() {
  try {
    kbs.value = await api.adminGetKnowledgeBases()
    kbMsg.value = ''
  } catch (e) {
    kbMsg.value = '加载知识库失败'
  }
}

function openKbCreate() {
  editingKb.value = { name: '', base_url: '', api_key: '', description: '', enabled: 1 }
}

function openKbEdit(kb) {
  editingKb.value = {
    id: kb.id,
    name: kb.name,
    base_url: kb.base_url,
    api_key: '',
    description: kb.description,
    enabled: kb.enabled,
  }
}

async function saveKb() {
  if (!editingKb.value) return
  const f = editingKb.value
  if (!f.name || !f.base_url) return (kbMsg.value = '请填写名称和地址')
  savingKb.value = true
  kbMsg.value = ''
  try {
    const body = { name: f.name, base_url: f.base_url, description: f.description || '', enabled: f.enabled }
    if (f.api_key) body.api_key = f.api_key
    if (f.id) {
      await api.adminUpdateKnowledgeBase(f.id, body)
    } else {
      await api.adminCreateKnowledgeBase(body)
    }
    editingKb.value = null
    await loadKbs()
  } catch (e) {
    kbMsg.value = e.message
  } finally {
    savingKb.value = false
  }
}

async function delKb(kb) {
  if (!confirm(`删除知识库「${kb.name}」？`)) return
  try {
    await api.adminDeleteKnowledgeBase(kb.id)
    await loadKbs()
  } catch (e) {
    kbMsg.value = e.message
  }
}

async function loadBots() {
  try {
    bots.value = await api.adminGetWecomBots()
    botMsg.value = ''
  } catch {
    botMsg.value = '加载企微机器人失败'
  }
}

function openBotCreate() {
  editingBot.value = {
    name: '',
    corp_id: '',
    secret: '',
    agent_id: '',
    token: '',
    aes_key: '',
    kb_ids: [],
    web_search: 0,
    endpoint_id: null,
    model: '',
    enabled: 1,
  }
}

function openBotEdit(b) {
  editingBot.value = {
    id: b.id,
    name: b.name,
    corp_id: b.corp_id,
    secret: '',
    agent_id: b.agent_id,
    token: '',
    aes_key: '',
    token_masked: b.token_masked,
    aes_key_set: b.aes_key_set,
    callback_url: b.callback_url,
    kb_ids: (b.kb_ids || '').split(',').filter(Boolean).map(Number),
    web_search: b.web_search,
    endpoint_id: b.endpoint_id,
    model: b.model,
    enabled: b.enabled,
  }
}

const botModelOptions = computed(() => {
  if (!editingBot.value || !editingBot.value.endpoint_id) return []
  const ep = endpoints.value.find((e) => e.id === editingBot.value.endpoint_id)
  if (!ep) return []
  return String(ep.models || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
})

function toggleBotKb(kbId) {
  const arr = editingBot.value.kb_ids
  const idx = arr.indexOf(kbId)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(kbId)
}

async function saveBot() {
  if (!editingBot.value) return
  const f = editingBot.value
  if (!f.name) return (botMsg.value = '请填写机器人名称')
  savingBot.value = true
  botMsg.value = ''
  try {
    const body = {
      name: f.name,
      corp_id: f.corp_id,
      agent_id: f.agent_id,
      token: f.token,
      kb_ids: (f.kb_ids || []).join(','),
      web_search: f.web_search || 0,
      endpoint_id: f.endpoint_id || null,
      model: f.model,
      enabled: f.enabled,
    }
    if (f.secret) body.secret = f.secret
    if (f.aes_key) body.aes_key = f.aes_key
    if (f.id) {
      await api.adminUpdateWecomBot(f.id, body)
    } else {
      await api.adminCreateWecomBot(body)
    }
    editingBot.value = null
    await loadBots()
  } catch (e) {
    botMsg.value = e.message
  } finally {
    savingBot.value = false
  }
}

async function delBot(b) {
  if (!confirm(`删除机器人「${b.name}」？`)) return
  try {
    await api.adminDeleteWecomBot(b.id)
    await loadBots()
  } catch (e) {
    botMsg.value = e.message
  }
}

async function delUser(u) {
  if (!confirm(`删除用户「${u.nickname}」（连同其会话、消息与附件）？`)) return
  try {
    await api.adminDeleteUser(u.id)
    await Promise.all([loadUsers(), loadStats()])
  } catch (e) {
    errorMsg.value = e.message
  }
}

async function loadWecom() {
  try {
    const w = await api.adminGetWecom()
    wecomCorpId.value = w.wecom_corp_id
    wecomAgentId.value = w.wecom_agent_id
    wecomRedirect.value = w.wecom_redirect
    wecomSecretSet.value = w.wecom_secret_set
  } catch {
    wecomMsg.value = '加载企业微信配置失败'
  }
}

async function saveWecom() {
  savingWecom.value = true
  wecomMsg.value = ''
  try {
    const body = {
      wecom_corp_id: wecomCorpId.value,
      wecom_agent_id: wecomAgentId.value,
      wecom_redirect: wecomRedirect.value,
    }
    if (wecomSecret.value) body.wecom_secret = wecomSecret.value
    await api.adminSaveWecom(body)
    wecomSecret.value = ''
    wecomMsg.value = '已保存'
    await loadWecom()
  } catch (e) {
    wecomMsg.value = e.message
  } finally {
    savingWecom.value = false
  }
}

async function loadLogo() {
  try {
    const r = await api.adminGetLogo()
    logoSet.value = r.logo_set
    logoPreview.value = r.logo_set ? '/api/logo?t=' + Date.now() : ''
  } catch {
    logoSet.value = false
    logoPreview.value = ''
  }
}

function onLogoFile(e) {
  const f = e.target.files[0]
  if (!f) return
  logoFile.value = f
  logoPreview.value = URL.createObjectURL(f)
  logoMsg.value = ''
}

async function uploadLogo() {
  if (!logoFile.value) return (logoMsg.value = '请选择图片文件')
  savingLogo.value = true
  logoMsg.value = ''
  try {
    const r = await api.adminUploadLogo(logoFile.value)
    logoSet.value = r.logo_set
    logoMsg.value = 'Logo 已保存'
    await loadLogo()
  } catch (e) {
    logoMsg.value = e.message
  } finally {
    savingLogo.value = false
  }
}

async function resetLogo() {
  if (!confirm('恢复默认 Logo（删除自定义 Logo）？')) return
  try {
    await api.adminDeleteLogo()
    logoFile.value = null
    logoSet.value = false
    logoPreview.value = ''
    logoMsg.value = '已恢复默认 Logo'
  } catch (e) {
    logoMsg.value = e.message
  }
}

function openCreate() {
  editing.value = { name: '', base_url: '', api_key: '', models: '', enabled: 1, is_default: 0 }
}

function openEdit(e) {
  editing.value = { id: e.id, name: e.name, base_url: e.base_url, api_key: '', models: e.models, enabled: e.enabled, is_default: e.is_default }
}

async function save() {
  if (!editing.value) return
  const f = editing.value
  if (!f.name || !f.base_url) return (errorMsg.value = '请填写名称和 base_url')
  errorMsg.value = ''
  try {
    if (f.id) {
      const body = { name: f.name, base_url: f.base_url, models: f.models, enabled: f.enabled, is_default: f.is_default }
      if (f.api_key) body.api_key = f.api_key
      await api.adminUpdateEndpoint(f.id, body)
    } else {
      await api.adminCreateEndpoint({
        name: f.name,
        base_url: f.base_url,
        api_key: f.api_key,
        models: f.models,
        enabled: f.enabled,
        is_default: f.is_default,
      })
    }
    editing.value = null
    await load()
  } catch (e) {
    errorMsg.value = e.message
  }
}

async function del(e) {
  if (!confirm(`删除接口「${e.name}」？`)) return
  await api.adminDeleteEndpoint(e.id)
  await load()
}

async function changePassword() {
  if (!oldPwd.value || !newPwd.value) return (pwdMsg.value = '请填写当前密码和新密码')
  if (newPwd.value !== confirmPwd.value) return (pwdMsg.value = '两次输入的新密码不一致')
  savingPwd.value = true
  pwdMsg.value = ''
  try {
    await api.adminChangePassword({ old_password: oldPwd.value, new_password: newPwd.value })
    pwdMsg.value = '密码已修改'
    oldPwd.value = newPwd.value = confirmPwd.value = ''
  } catch (e) {
    pwdMsg.value = e.message
  } finally {
    savingPwd.value = false
  }
}

function logout() {
  store.logoutAdmin()
  endpoints.value = []
  stats.value = null
  users.value = []
}

function fmtDate(s) {
  if (!s) return '—'
  return String(s).replace('T', ' ').slice(0, 16)
}

onMounted(() => {
  if (isAdmin()) load()
})
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
          <button
            v-for="n in navItems"
            :key="n.key"
            class="nav-item"
            :class="{ active: active === n.key }"
            @click="selectSection(n.key)"
          >
            {{ n.label }}
          </button>
        </nav>
        <div class="side-foot">
          <button class="nav-item" @click="logout">退出登录</button>
        </div>
      </aside>

      <main class="admin-main">
        <section v-if="active === 'dashboard'" class="content">
          <div class="head">
            <h2>首页</h2>
            <button class="btn btn-outline" @click="loadStats">刷新</button>
          </div>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-num">{{ stats?.users ?? 0 }}</div>
              <div class="stat-label">注册用户</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats?.conversations ?? 0 }}</div>
              <div class="stat-label">会话数</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats?.messages ?? 0 }}</div>
              <div class="stat-label">消息数</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats?.endpoints ?? 0 }}</div>
              <div class="stat-label">LLM 接口</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats?.attachments ?? 0 }}</div>
              <div class="stat-label">上传附件</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats?.today_tokens ?? 0 }}</div>
              <div class="stat-label">今日 Token</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats?.month_tokens ?? 0 }}</div>
              <div class="stat-label">本月 Token</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats?.total_tokens ?? 0 }}</div>
              <div class="stat-label">总 Token</div>
            </div>
          </div>

          <h3 class="section-title">接口启用状态</h3>
          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>base_url</th>
                <th>默认</th>
                <th>启用</th>
                <th>今日 Token</th>
                <th>本月 Token</th>
                <th>总 Token</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in endpointsUsage" :key="e.id">
                <td>{{ e.name }}</td>
                <td class="mono">{{ e.base_url }}</td>
                <td>{{ e.is_default ? '●' : '' }}</td>
                <td>{{ e.enabled ? '✓' : '✕' }}</td>
                <td>{{ e.today_tokens }}</td>
                <td>{{ e.month_tokens }}</td>
                <td>{{ e.total_tokens }}</td>
              </tr>
              <tr v-if="!endpointsUsage.length">
                <td colspan="7" class="empty">暂无接口</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-else-if="active === 'users'" class="content">
          <div class="head">
            <h2>用户列表</h2>
            <button class="btn btn-outline" @click="loadUsers">刷新</button>
          </div>
          <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

          <table class="table">
            <thead>
              <tr>
                <th>昵称</th>
                <th>手机号</th>
                <th>会话数</th>
                <th>总 Token</th>
                <th>当天 Token</th>
                <th>注册时间</th>
                <th>最近活跃</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td>{{ u.nickname }}</td>
                <td>{{ u.phone || '—' }}</td>
                <td>{{ u.conversation_count }}</td>
                <td>{{ u.total_tokens }}</td>
                <td>{{ u.today_tokens }}</td>
                <td>{{ fmtDate(u.created_at) }}</td>
                <td>{{ fmtDate(u.last_active) }}</td>
                <td>
                  <button class="btn-ghost del" @click="delUser(u)">删除</button>
                </td>
              </tr>
              <tr v-if="!users.length">
                <td colspan="8" class="empty">暂无用户</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-else-if="active === 'endpoints'" class="content">
          <div class="head">
            <h2>接口设置</h2>
            <button class="btn" @click="openCreate">＋ 添加接口</button>
          </div>
          <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>base_url</th>
                <th>模型</th>
                <th>默认</th>
                <th>启用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in endpoints" :key="e.id">
                <td>{{ e.name }}</td>
                <td class="mono">{{ e.base_url }}</td>
                <td>{{ e.models }}</td>
                <td>{{ e.is_default ? '●' : '' }}</td>
                <td>{{ e.enabled ? '✓' : '✕' }}</td>
                <td>
                  <button class="btn-ghost" @click="openEdit(e)">编辑</button>
                  <button class="btn-ghost del" @click="del(e)">删除</button>
                </td>
              </tr>
              <tr v-if="!endpoints.length">
                <td colspan="6" class="empty">暂无接口，点击「添加接口」创建</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-else-if="active === 'sms'" class="content">
          <h2>短信接口</h2>
          <div class="card">
            <label class="sm-label">服务商
              <select v-model="smsProvider" class="input">
                <option v-for="p in smsProviders" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
            </label>
            <div class="sms-grid">
              <label>AccessKey ID / SecretId<input v-model="smsAccessKeyId" class="input" placeholder="阿里云 AccessKey ID / 腾讯云 SecretId" /></label>
              <label>密钥 Secret<input v-model="smsSecret" type="password" class="input" :placeholder="smsSecretSet ? '已设置（留空不修改）' : 'AccessKey Secret / SecretKey'" /></label>
              <label>签名 SignName<input v-model="smsSignName" class="input" placeholder="短信签名" /></label>
              <label>模板 CODE<input v-model="smsTemplateCode" class="input" placeholder="如 SMS_123456 / 模板ID" /></label>
              <label>地域 Region<input v-model="smsRegion" class="input" placeholder="如 cn-hangzhou / ap-guangzhou" /></label>
              <label v-if="smsProvider === 'tencent'">SDKAppID<input v-model="smsSdkAppId" class="input" placeholder="腾讯云 SDKAppID" /></label>
            </div>
            <p class="hint" style="margin-top: 10px">
              {{ smsProvider === 'aliyun' ? '阿里云短信：需在控制台创建签名与模板，模板变量为 code。' : (smsProvider === 'tencent' ? '腾讯云短信：需 SDKAppID、签名与模板，模板变量为 code。' : (smsProvider ? '' : '未启用短信服务，关闭调试后无法使用手机号登录。')) }}
            </p>
            <div class="card-foot">
              <p v-if="smsMsg" class="hint">{{ smsMsg }}</p>
              <button class="btn" :disabled="savingSms" @click="saveSms">{{ savingSms ? '保存中…' : '保存短信配置' }}</button>
            </div>
          </div>
        </section>

        <section v-else-if="active === 'search'" class="content">
          <h2>联网搜索</h2>
          <div class="card">
            <div class="sms-grid">
              <label>搜索来源
                <select v-model="searchProvider" class="input">
                  <option v-for="p in searchProviders" :key="p.value" :value="p.value">{{ p.label }}</option>
                </select>
              </label>
              <label>API Key
                <input v-model="searchApiKey" type="password" class="input" :placeholder="searchApiKeySet ? '已设置（留空不修改）' : 'API Key'" />
              </label>
            </div>
            <label v-if="searchProvider === 'searxng'" class="sm-label">SearXNG 地址
              <input v-model="searchBaseUrl" class="input" placeholder="如 https://searx.example" />
            </label>
            <label class="debug-row" style="margin-top: 12px">
              <input type="checkbox" v-model="searchAuto" />
              <span>自动识别搜索（无需手动开启联网）</span>
            </label>
            <p class="hint" style="margin-top: 8px">
              开启后，聊天可调用联网搜索补充实时信息。手动开启时用户可在输入框旁点「联网」；自动模式下模型按需自主搜索。Tavily / Bing 需 API Key，SearXNG 需自托管地址，DuckDuckGo 免 Key 但结果有限。
            </p>
            <div class="card-foot">
              <p v-if="searchMsg" class="hint">{{ searchMsg }}</p>
              <button class="btn" :disabled="savingSearch" @click="saveSearch">{{ savingSearch ? '保存中…' : '保存搜索配置' }}</button>
            </div>
          </div>
        </section>

        <section v-else-if="active === 'knowledge'" class="content">
          <div class="head">
            <h2>知识库</h2>
            <button class="btn" @click="openKbCreate">＋ 添加知识库</button>
          </div>
          <p v-if="kbMsg" class="msg">{{ kbMsg }}</p>
          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>地址</th>
                <th>说明</th>
                <th>启用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="kb in kbs" :key="kb.id">
                <td>{{ kb.name }}</td>
                <td class="mono">{{ kb.base_url }}</td>
                <td>{{ kb.description || '—' }}</td>
                <td>{{ kb.enabled ? '✓' : '✕' }}</td>
                <td>
                  <button class="btn-ghost" @click="openKbEdit(kb)">编辑</button>
                  <button class="btn-ghost del" @click="delKb(kb)">删除</button>
                </td>
              </tr>
              <tr v-if="!kbs.length">
                <td colspan="5" class="empty">暂无知识库，点击「添加知识库」创建</td>
              </tr>
            </tbody>
          </table>
          <p class="hint" style="margin-top: 10px">
            知识库为外部检索接口：聊天时按固定契约向「地址」POST <code>{ query, top_k }</code>（带 Bearer 密钥），并解析 <code>{ results: [{ title, content, source }] }</code>。用户在前台选择知识库后，系统会检索并把相关内容注入给大模型回答。
          </p>
        </section>

        <section v-else-if="active === 'wecom'" class="content">
          <h2>企微设置</h2>
          <div class="card">
            <div class="wecom-grid">
              <label>CorpID<input v-model="wecomCorpId" class="input" placeholder="企业微信 CorpID" /></label>
              <label>Secret<input v-model="wecomSecret" type="password" class="input" :placeholder="wecomSecretSet ? '已设置（留空不修改）' : '应用 Secret'" /></label>
              <label>AgentId<input v-model="wecomAgentId" class="input" placeholder="应用 AgentId" /></label>
              <label>回调域名<input v-model="wecomRedirect" class="input" placeholder="如 https://your.domain" /></label>
            </div>
            <div class="card-foot">
              <p v-if="wecomMsg" class="hint">{{ wecomMsg }}</p>
              <button class="btn" :disabled="savingWecom" @click="saveWecom">{{ savingWecom ? '保存中…' : '保存企业微信配置' }}</button>
            </div>
          </div>
        </section>

        <section v-else-if="active === 'wecom-bot'" class="content">
          <div class="head">
            <h2>企微机器人</h2>
            <button class="btn" @click="openBotCreate">＋ 添加机器人</button>
          </div>
          <p v-if="botMsg" class="msg">{{ botMsg }}</p>
          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>AgentId</th>
                <th>联网</th>
                <th>知识库</th>
                <th>启用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="b in bots" :key="b.id">
                <td>{{ b.name }}</td>
                <td class="mono">{{ b.agent_id }}</td>
                <td>{{ b.web_search ? '✓' : '✕' }}</td>
                <td>{{ b.kb_ids || '—' }}</td>
                <td>{{ b.enabled ? '✓' : '✕' }}</td>
                <td>
                  <button class="btn-ghost" @click="openBotEdit(b)">编辑</button>
                  <button class="btn-ghost del" @click="delBot(b)">删除</button>
                </td>
              </tr>
              <tr v-if="!bots.length">
                <td colspan="6" class="empty">暂无机器人，点击「添加机器人」创建</td>
              </tr>
            </tbody>
          </table>
          <p class="hint" style="margin-top: 10px">
            每个机器人对应企微的一个自建应用。请在企微后台为该应用开通「API 接收消息」，回调地址填该机器人的回调 URL（编辑弹窗内显示），并填写 Token 与 EncodingAESKey。创建/编辑后可在弹窗底部看到回调地址。
          </p>
        </section>

        <section v-else-if="active === 'logo'" class="content">
          <h2>Logo设置</h2>
          <div class="card">
            <div class="logo-row">
              <div class="logo-preview">
                <img v-if="logoPreview" :src="logoPreview" alt="Logo 预览" />
                <span v-else class="logo-empty">未设置自定义 Logo（使用默认）</span>
              </div>
              <div class="logo-ops">
                <label class="btn btn-outline link file-btn">
                  {{ logoFile ? logoFile.name : '选择图片' }}
                  <input type="file" accept="image/*" @change="onLogoFile" />
                </label>
                <button class="btn" :disabled="savingLogo || !logoFile" @click="uploadLogo">
                  {{ savingLogo ? '上传中…' : '上传 Logo' }}
                </button>
                <button v-if="logoSet" class="btn-ghost del" @click="resetLogo">恢复默认</button>
              </div>
            </div>
            <p v-if="logoMsg" class="hint">{{ logoMsg }}</p>
            <p class="hint">上传后登录页与聊天侧边栏将显示该 Logo；图片建议使用透明背景 PNG 或 SVG。</p>
          </div>
        </section>

        <section v-else-if="active === 'system'" class="content">
          <h2>系统设置</h2>

          <h3 class="section-title">界面主题</h3>
          <div class="theme-card">
            <div class="theme-options" role="radiogroup">
              <label
                v-for="opt in themeOptions"
                :key="opt.value"
                class="theme-radio"
                :class="{ selected: theme === opt.value }"
              >
                <input type="radio" :value="opt.value" v-model="theme" />
                <span class="theme-swatch" :class="'swatch-' + opt.value"></span>
                <span>{{ opt.label }}</span>
              </label>
            </div>
            <div class="theme-foot">
              <p v-if="themeMsg" class="hint">{{ themeMsg }}</p>
              <button class="btn" :disabled="savingTheme" @click="saveTheme">{{ savingTheme ? '保存中…' : '保存主题' }}</button>
            </div>
          </div>

          <h3 class="section-title">调试选项</h3>
          <div class="theme-card">
            <label class="debug-row">
              <input type="checkbox" v-model="debugMode" :disabled="savingDebug" @change="toggleDebug" />
              <span>开启调试模式</span>
            </label>
            <p class="hint" style="margin-top: 8px">开启后，登录页可使用「模拟验证码」与「模拟扫码登录」；关闭后仅允许真实登录。</p>
            <p v-if="debugMsg" class="hint" style="margin-top: 6px">{{ debugMsg }}</p>
          </div>

          <h3 class="section-title">系统标题</h3>
          <div class="card">
            <label class="sm-label">网站标题
              <input v-model="siteTitle" class="input" placeholder="如 AI 助手" @keyup.enter="saveSite" />
            </label>
            <div class="card-foot">
              <p v-if="siteMsg" class="hint">{{ siteMsg }}</p>
              <button class="btn" :disabled="savingSite" @click="saveSite">{{ savingSite ? '保存中…' : '保存标题' }}</button>
            </div>
            <p class="hint" style="margin-top: 8px">保存后浏览器标签页标题将更新。</p>
          </div>

          <h3 class="section-title">助手默认名称</h3>
          <div class="card">
            <label class="sm-label">助手昵称
              <input v-model="assistantName" class="input" placeholder="如 AI 助手" @keyup.enter="saveAssistantName" />
            </label>
            <div class="card-foot">
              <p v-if="assistantMsg" class="hint">{{ assistantMsg }}</p>
              <button class="btn" :disabled="savingAssistant" @click="saveAssistantName">{{ savingAssistant ? '保存中…' : '保存助手名称' }}</button>
            </div>
            <p class="hint" style="margin-top: 8px">聊天气泡中助手显示的默认昵称；留空时默认为 askai。用户可在个人资料中覆盖为自己的助手名。</p>
          </div>

          <h3 class="section-title">浏览器图标（Favicon）</h3>
          <div class="card">
            <div class="logo-row">
              <div class="logo-preview favicon-preview">
                <img v-if="faviconPreview" :src="faviconPreview" alt="Favicon 预览" />
                <span v-else class="logo-empty">未设置自定义图标（使用默认）</span>
              </div>
              <div class="logo-ops">
                <label class="btn btn-outline link file-btn">
                  {{ faviconFile ? faviconFile.name : '选择图片' }}
                  <input type="file" accept="image/*" @change="onFaviconFile" />
                </label>
                <button class="btn" :disabled="savingFavicon || !faviconFile" @click="uploadFavicon">
                  {{ savingFavicon ? '上传中…' : '上传 Favicon' }}
                </button>
                <button v-if="faviconSet" class="btn-ghost del" @click="resetFavicon">恢复默认</button>
              </div>
            </div>
            <p v-if="faviconMsg" class="hint">{{ faviconMsg }}</p>
            <p class="hint">上传后浏览器标签页图标将更新；建议使用 32x32 或 64x64 的 PNG/ICO。</p>
          </div>

          <h3 class="section-title">助手默认头像</h3>
          <div class="card">
            <div class="logo-row">
              <div class="logo-preview favicon-preview">
                <img v-if="assistantAvatarPreview" :src="assistantAvatarPreview" alt="助手默认头像预览" />
                <span v-else class="logo-empty">未设置（使用首字母占位）</span>
              </div>
              <div class="logo-ops">
                <label class="btn btn-outline link file-btn">
                  {{ assistantAvatarFile ? assistantAvatarFile.name : '选择图片' }}
                  <input type="file" accept="image/*" @change="onAssistantAvatarFile" />
                </label>
                <button class="btn" :disabled="savingAssistantAvatar || !assistantAvatarFile" @click="uploadAssistantAvatar">
                  {{ savingAssistantAvatar ? '上传中…' : '上传助手头像' }}
                </button>
                <button v-if="assistantAvatarSet" class="btn-ghost del" @click="resetAssistantAvatar">恢复默认</button>
              </div>
            </div>
            <p v-if="assistantAvatarMsg" class="hint">{{ assistantAvatarMsg }}</p>
            <p class="hint">当用户在个人资料中未设置自定义助手头像时，聊天气泡将显示此默认头像。</p>
          </div>

          <h3 class="section-title">后台随机地址</h3>
          <div class="card">
            <label class="debug-row">
              <input type="checkbox" v-model="adminEnabled" />
              <span>开启随机后台地址</span>
            </label>
            <p class="hint" style="margin-top: 8px">开启后，仅能通过 <code>https://你的域名/admin?r=随机参数</code> 进入后台，否则显示 404。</p>
            <label class="sm-label">随机参数
              <input v-model="adminSecret" class="input mono" placeholder="留空自动生成" />
            </label>
            <div class="row-btn">
              <button class="btn btn-outline" @click="generateAdminSecret">随机生成</button>
              <button class="btn" :disabled="savingAdmin" @click="saveAdminSecret">{{ savingAdmin ? '保存中…' : '保存设置' }}</button>
            </div>
            <p v-if="adminMsg" class="hint" style="margin-top: 8px">{{ adminMsg }}</p>
            <p v-if="adminEnabled && adminSecret" class="hint" style="margin-top: 8px">
              后台访问地址：<code>{{ adminUrl }}</code>
            </p>
          </div>
        </section>

        <section v-else class="content">
          <h2>修改密码</h2>
          <div class="card card-form">
            <label>当前密码<input v-model="oldPwd" type="password" class="input" placeholder="请输入当前密码" @keyup.enter="changePassword" /></label>
            <label>新密码<input v-model="newPwd" type="password" class="input" placeholder="至少 6 位" @keyup.enter="changePassword" /></label>
            <label>确认新密码<input v-model="confirmPwd" type="password" class="input" placeholder="再次输入新密码" @keyup.enter="changePassword" /></label>
            <p v-if="pwdMsg" class="hint" :class="{ 'hint-danger': pwdMsg.includes('不正确') || pwdMsg.includes('一致') || pwdMsg.includes('至少') }">{{ pwdMsg }}</p>
            <button class="btn" :disabled="savingPwd" @click="changePassword">{{ savingPwd ? '提交中…' : '修改密码' }}</button>
          </div>
        </section>
      </main>
    </template>

    <div v-if="editing" class="modal-mask" @click.self="editing = null">
      <div class="modal">
        <h3>{{ editing.id ? '编辑接口' : '添加接口' }}</h3>
        <label>名称<input v-model="editing.name" class="input" placeholder="如 OpenAI" /></label>
        <label>base_url<input v-model="editing.base_url" class="input" placeholder="https://api.openai.com/v1" /></label>
        <label>API Key<input v-model="editing.api_key" type="password" class="input" :placeholder="editing.id ? '留空则不修改' : '请输入 API Key'" /></label>
        <label>模型列表（逗号分隔）<textarea v-model="editing.models" class="input" rows="2" placeholder="gpt-4o, gpt-4o-mini"></textarea></label>
        <label class="check"><input type="checkbox" v-model="editing.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <label class="check"><input type="checkbox" v-model="editing.is_default" :true-value="1" :false-value="0" /> 设为默认接口</label>
        <div class="foot">
          <button class="btn btn-outline" @click="editing = null">取消</button>
          <button class="btn" @click="save">保存</button>
        </div>
      </div>
    </div>

    <div v-if="editingKb" class="modal-mask" @click.self="editingKb = null">
      <div class="modal">
        <h3>{{ editingKb.id ? '编辑知识库' : '添加知识库' }}</h3>
        <label>名称<input v-model="editingKb.name" class="input" placeholder="如 内部文档" /></label>
        <label>检索接口地址<input v-model="editingKb.base_url" class="input" placeholder="如 https://kb.example/retrieve" /></label>
        <label>API Key<input v-model="editingKb.api_key" type="password" class="input" :placeholder="editingKb.id ? '留空则不修改' : '可选，Bearer 密钥'" /></label>
        <label>说明<textarea v-model="editingKb.description" class="input" rows="2" placeholder="知识库简介（可选）"></textarea></label>
        <label class="check"><input type="checkbox" v-model="editingKb.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <div class="foot">
          <button class="btn btn-outline" @click="editingKb = null">取消</button>
          <button class="btn" :disabled="savingKb" @click="saveKb">{{ savingKb ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="editingBot" class="modal-mask" @click.self="editingBot = null">
      <div class="modal">
        <h3>{{ editingBot.id ? '编辑机器人' : '添加机器人' }}</h3>
        <label>名称<input v-model="editingBot.name" class="input" placeholder="如 客服机器人" /></label>
        <div class="form-2">
          <label>CorpID<input v-model="editingBot.corp_id" class="input" placeholder="留空使用企微设置中的 CorpID" /></label>
          <label>应用 Secret<input v-model="editingBot.secret" type="password" class="input" :placeholder="editingBot.id ? '留空不修改' : '应用 Secret'" /></label>
          <label>AgentId<input v-model="editingBot.agent_id" class="input" placeholder="应用 AgentId" /></label>
          <label>Token<input v-model="editingBot.token" type="password" class="input" :placeholder="editingBot.id ? (editingBot.token_masked || '已设置（留空不修改）') : '回调 Token'" /></label>
          <label>EncodingAESKey<input v-model="editingBot.aes_key" type="password" class="input" :placeholder="editingBot.id ? '已设置（留空不修改）' : 'EncodingAESKey'" /></label>
        </div>
        <label>接口
          <select v-model="editingBot.endpoint_id" class="input">
            <option :value="null">默认接口</option>
            <option v-for="e in endpoints" :key="e.id" :value="e.id">{{ e.name }}</option>
          </select>
        </label>
        <label>模型
          <select v-model="editingBot.model" class="input">
            <option value="">自动（接口默认）</option>
            <option v-for="m in botModelOptions" :key="m" :value="m">{{ m }}</option>
          </select>
        </label>
        <div class="form-2">
          <label>知识库
            <div class="kb-checkbox-list">
              <label v-for="kb in kbs" :key="kb.id" class="check">
                <input type="checkbox" :value="kb.id" :checked="editingBot.kb_ids.includes(kb.id)" @change="toggleBotKb(kb.id)" />
                {{ kb.name }}
              </label>
              <span v-if="!kbs.length" class="hint">暂无知识库</span>
            </div>
          </label>
          <label class="check" style="margin-top: 10px"><input type="checkbox" v-model="editingBot.web_search" :true-value="1" :false-value="0" /> 启用联网搜索</label>
        </div>
        <label class="check"><input type="checkbox" v-model="editingBot.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <p v-if="editingBot.id" class="hint" style="margin-top: 8px">
          回调地址：<code>{{ editingBot.callback_url }}</code>
        </p>
        <p v-if="!editingBot.id" class="hint" style="margin-top: 8px">保存后可在此查看回调地址，填入企微后台。</p>
        <div class="foot">
          <button class="btn btn-outline" @click="editingBot = null">取消</button>
          <button class="btn" :disabled="savingBot" @click="saveBot">{{ savingBot ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
  gap: 4px;
}

.nav-item {
  text-align: left;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text-muted);
  text-decoration: none;
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

.full {
  width: 100%;
}
</style>
