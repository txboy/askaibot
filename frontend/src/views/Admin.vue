<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { store } from '../store'
import { applyTheme } from '../theme'
import Logo from '../components/Logo.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { useConfirm } from '../composables/useConfirm'

const confirmDlg = useConfirm()

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
  { key: 'mcp', label: 'MCP 工具' },
  { key: 'skill', label: '技能包' },
  { key: 'knowledge', label: '知识库' },
  { key: 'wecom', label: '企微设置' },
  { key: 'dingtalk', label: '钉钉设置' },
  { key: 'feishu', label: '飞书设置' },
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

const dingtalkAppKey = ref('')
const dingtalkSecret = ref('')
const dingtalkAgentId = ref('')
const dingtalkRedirect = ref('')
const dingtalkSecretSet = ref(false)
const dingtalkMsg = ref('')
const savingDingtalk = ref(false)

const feishuAppId = ref('')
const feishuSecret = ref('')
const feishuRedirect = ref('')
const feishuSecretSet = ref(false)
const feishuMsg = ref('')
const savingFeishu = ref(false)

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
const captchaMsg = ref('')
const savingCaptcha = ref(false)
const smsProviders = [
  { value: '', label: '不启用' },
  { value: 'aliyun', label: '阿里云' },
  { value: 'tencent', label: '腾讯云' },
]
const smsCaptchaEnabled = ref(true)
const smsCaptchaProvider = ref('builtin')
const smsCooldown = ref(60)
const geetestCaptchaId = ref('')
const geetestCaptchaKey = ref('')
const geetestKeySet = ref(false)
const tencentCaptchaAppId = ref('')
const tencentCaptchaKey = ref('')
const tencentKeySet = ref(false)
const aliyunCaptchaAccessKeyId = ref('')
const aliyunCaptchaSecret = ref('')
const aliyunSecretSet = ref(false)
const aliyunSceneId = ref('')
const captchaProviders = [
  { value: 'builtin', label: '自建图片验证码' },
  { value: 'geetest', label: '极验 v4' },
  { value: 'tencent', label: '腾讯云天御' },
  { value: 'aliyun', label: '阿里云验证码 2.0' },
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
const testingKb = ref(false)
const kbTestResult = ref('')
const editingKb = ref(null)

const bots = ref([])
const botMsg = ref('')
const savingBot = ref(false)
const editingBot = ref(null)

const mcps = ref([])
const mcpMsg = ref('')
const savingMcp = ref(false)
const editingMcp = ref(null)
const mcpTestTools = ref(null)
const mcpTransports = [
  { value: 'http', label: 'HTTP（Streamable HTTP）' },
  { value: 'stdio', label: '本地 stdio 子进程' },
]
const mcpModes = [
  { value: 'llm', label: '大模型选用（默认注入）' },
  { value: 'frontend', label: '前端选用（用户勾选）' },
]

const skills = ref([])
const skillMsg = ref('')
const savingSkill = ref(false)
const editingSkill = ref(null)
const skillTest = ref(null)
const skillUploadFile = ref(null)
const skillUploadScope = ref('global')
const skillUploadEnabled = ref(true)
const skillScopes = [
  { value: 'global', label: '全部用户' },
  { value: 'user', label: '指定用户' },
]

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
    await Promise.all([loadEndpoints(), loadWecom(), loadDingtalk(), loadFeishu(), loadLogo(), loadStats(), loadUsers(), loadEndpointsUsage(), loadTheme(), loadDebug(), loadSms(), loadSystem(), loadKbs(), loadBots('wecom'), loadMcps(), loadSkills()])
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
    else if (key === 'mcp') await loadMcps()
    else if (key === 'skill') await loadSkills()
    else if (key === 'knowledge') await loadKbs()
    else if (key === 'wecom') { await loadWecom(); await loadBots('wecom') }
    else if (key === 'dingtalk') { await loadDingtalk(); await loadBots('dingtalk') }
    else if (key === 'feishu') { await loadFeishu(); await loadBots('feishu') }
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
  if (!(await confirmDlg.askConfirm('恢复默认图标（删除自定义 favicon）？', { title: '恢复默认 favicon' }))) return
  try {
    await api.adminDeleteFavicon()
    faviconFile.value = null
    faviconSet.value = false
    faviconPreview.value = ''
    const link = document.querySelector("link[rel~='icon']")
    if (link) link.href = '/favicon.ico'
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
  if (!(await confirmDlg.askConfirm('恢复默认（删除助手默认头像）？', { title: '恢复默认头像' }))) return
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
    smsCaptchaEnabled.value = !!r.captcha_enabled
    smsCaptchaProvider.value = r.captcha_provider || 'builtin'
    smsCooldown.value = r.cooldown || 60
    geetestCaptchaId.value = r.geetest_captcha_id
    geetestCaptchaKey.value = ''
    geetestKeySet.value = r.geetest_key_set
    tencentCaptchaAppId.value = r.tencent_captcha_app_id
    tencentCaptchaKey.value = ''
    tencentKeySet.value = r.tencent_key_set
    aliyunCaptchaAccessKeyId.value = r.aliyun_access_key_id
    aliyunCaptchaSecret.value = ''
    aliyunSecretSet.value = r.aliyun_secret_set
    aliyunSceneId.value = r.aliyun_scene_id
    smsSecret.value = ''
    smsMsg.value = ''
    captchaMsg.value = ''
  } catch (e) {
    smsMsg.value = '加载短信配置失败'
  }
}

function buildCaptchaBody() {
  const body = {
    captcha_enabled: smsCaptchaEnabled.value,
    captcha_provider: smsCaptchaProvider.value,
    cooldown: Number(smsCooldown.value) || 60,
  }
  if (geetestCaptchaId.value) body.geetest_captcha_id = geetestCaptchaId.value
  if (geetestCaptchaKey.value) body.geetest_captcha_key = geetestCaptchaKey.value
  if (tencentCaptchaAppId.value) body.tencent_captcha_app_id = tencentCaptchaAppId.value
  if (tencentCaptchaKey.value) body.tencent_captcha_app_secret_key = tencentCaptchaKey.value
  if (aliyunCaptchaAccessKeyId.value) body.aliyun_access_key_id = aliyunCaptchaAccessKeyId.value
  if (aliyunCaptchaSecret.value) body.aliyun_access_key_secret = aliyunCaptchaSecret.value
  if (aliyunSceneId.value) body.aliyun_scene_id = aliyunSceneId.value
  return body
}

function resetCaptchaSecrets(r) {
  geetestCaptchaKey.value = ''
  geetestKeySet.value = r.geetest_key_set
  tencentCaptchaKey.value = ''
  tencentKeySet.value = r.tencent_key_set
  aliyunCaptchaSecret.value = ''
  aliyunSecretSet.value = r.aliyun_secret_set
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
    Object.assign(body, buildCaptchaBody())
    const r = await api.adminSaveSms(body)
    smsSecret.value = ''
    smsSecretSet.value = r.secret_set
    resetCaptchaSecrets(r)
    smsMsg.value = '已保存'
  } catch (e) {
    smsMsg.value = e.message
  } finally {
    savingSms.value = false
  }
}

async function saveCaptcha() {
  savingCaptcha.value = true
  captchaMsg.value = ''
  try {
    const r = await api.adminSaveSms(buildCaptchaBody())
    resetCaptchaSecrets(r)
    captchaMsg.value = '已保存'
  } catch (e) {
    captchaMsg.value = e.message
  } finally {
    savingCaptcha.value = false
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
  editingKb.value = { name: '', provider: 'dify', base_url: '', api_key: '', dataset_ids: '', top_k: 5, mode: 'frontend', description: '', enabled: 1 }
  kbTestResult.value = ''
}

function openKbEdit(kb) {
  editingKb.value = {
    id: kb.id,
    name: kb.name,
    provider: kb.provider || 'dify',
    base_url: kb.base_url,
    api_key: '',
    dataset_ids: kb.dataset_ids || '',
    top_k: kb.top_k || 5,
    mode: kb.mode || 'frontend',
    description: kb.description,
    enabled: kb.enabled,
  }
  kbTestResult.value = ''
}

async function saveKb() {
  if (!editingKb.value) return
  const f = editingKb.value
  if (!f.name || !f.base_url) return (kbMsg.value = '请填写名称和地址')
  savingKb.value = true
  kbMsg.value = ''
  try {
    const body = { name: f.name, provider: f.provider, base_url: f.base_url, dataset_ids: f.dataset_ids || '', top_k: Number(f.top_k) || 5, mode: f.mode, description: f.description || '', enabled: f.enabled }
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

async function testKb() {
  if (!editingKb.value) return
  const f = editingKb.value
  if (!f.base_url || !f.dataset_ids) return (kbTestResult.value = '请填写地址和数据集ID')
  testingKb.value = true
  kbTestResult.value = ''
  try {
    const res = await api.adminTestKnowledgeBase({
      provider: f.provider,
      base_url: f.base_url,
      api_key: f.api_key || '',
      dataset_ids: f.dataset_ids || '',
      top_k: Number(f.top_k) || 5,
      query: '测试',
    })
    const hits = res.results || []
    if (hits.length) {
      kbTestResult.value = `检索成功，命中 ${hits.length} 条：\n` + hits.map((h) => `- ${h.title || '片段'}`).join('\n')
    } else {
      kbTestResult.value = '检索成功，但未命中结果。'
    }
  } catch (e) {
    kbTestResult.value = '检索失败：' + (e.message || e)
  } finally {
    testingKb.value = false
  }
}

async function delKb(kb) {
  if (!(await confirmDlg.askConfirm(`删除知识库「${kb.name}」？`, { title: '删除知识库', danger: true }))) return
  try {
    await api.adminDeleteKnowledgeBase(kb.id)
    await loadKbs()
  } catch (e) {
    kbMsg.value = e.message
  }
}

async function loadBots(provider = 'wecom') {
  try {
    bots.value = await api.adminGetWecomBots(provider)
    botMsg.value = ''
  } catch {
    botMsg.value = '加载机器人失败'
  }
}

function openBotCreate(provider = 'wecom') {
  editingBot.value = {
    provider,
    name: '',
    corp_id: '',
    secret: '',
    agent_id: '',
    token: '',
    aes_key: '',
    kb_ids: [],
    mcp_ids: [],
    skill_ids: [],
    web_search: 0,
    endpoint_id: null,
    model: '',
    enabled: 1,
  }
}

function openBotEdit(b) {
  editingBot.value = {
    id: b.id,
    provider: b.provider || 'wecom',
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
    mcp_ids: (b.mcp_ids || '').split(',').filter(Boolean).map(Number),
    skill_ids: (b.skill_ids || '').split(',').filter(Boolean).map(Number),
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

const botIsDingtalk = computed(() => (editingBot.value?.provider || 'wecom') === 'dingtalk')
const botIsFeishu = computed(() => (editingBot.value?.provider || 'wecom') === 'feishu')

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
      provider: f.provider || 'wecom',
      corp_id: f.corp_id,
      agent_id: f.agent_id,
      token: f.token,
      kb_ids: (f.kb_ids || []).join(','),
      mcp_ids: (f.mcp_ids || []).join(','),
      skill_ids: (f.skill_ids || []).join(','),
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
    await loadBots(f.provider)
  } catch (e) {
    botMsg.value = e.message
  } finally {
    savingBot.value = false
  }
}

async function delBot(b) {
  if (!(await confirmDlg.askConfirm(`删除机器人「${b.name}」？`, { title: '删除机器人', danger: true }))) return
  try {
    await api.adminDeleteWecomBot(b.id)
    await loadBots(b.provider)
  } catch (e) {
    botMsg.value = e.message
  }
}

async function loadMcps() {
  try {
    mcps.value = await api.adminMcpServers()
    mcpMsg.value = ''
  } catch {
    mcpMsg.value = '加载 MCP 服务失败'
  }
}

function openMcpCreate() {
  editingMcp.value = {
    name: '',
    description: '',
    transport: 'http',
    url: '',
    headers: '',
    command: '',
    args: '[]',
    env: '{}',
    mode: 'llm',
    enabled: 1,
    tools: [],
  }
}

function openMcpEdit(m) {
  editingMcp.value = {
    id: m.id,
    name: m.name,
    description: m.description || '',
    transport: m.transport,
    url: m.url || '',
    headers: '',
    command: m.command || '',
    args: m.args || '[]',
    env: m.env || '{}',
    mode: m.mode,
    enabled: m.enabled,
    tools: m.tools || [],
  }
}

async function saveMcp() {
  if (!editingMcp.value) return
  const f = editingMcp.value
  if (!f.name) return (mcpMsg.value = '请填写服务名称')
  savingMcp.value = true
  mcpMsg.value = ''
  try {
    const body = {
      name: f.name,
      description: f.description || '',
      transport: f.transport,
      url: f.url || '',
      command: f.command || '',
      args: f.args || '[]',
      env: f.env || '{}',
      mode: f.mode,
      enabled: f.enabled,
    }
    if (f.transport === 'http' && f.headers) body.headers = f.headers
    if (f.id) {
      await api.adminUpdateMcp(f.id, body)
    } else {
      body.headers = f.headers || '{}'
      await api.adminCreateMcp(body)
    }
    editingMcp.value = null
    await loadMcps()
  } catch (e) {
    mcpMsg.value = e.message
  } finally {
    savingMcp.value = false
  }
}

async function delMcp(m) {
  if (!(await confirmDlg.askConfirm(`删除 MCP 服务「${m.name}」？`, { title: '删除 MCP 服务', danger: true }))) return
  try {
    await api.adminDeleteMcp(m.id)
    await loadMcps()
  } catch (e) {
    mcpMsg.value = e.message
  }
}

async function testMcp(m) {
  try {
    const tools = await api.adminTestMcp(m.id)
    mcpTestTools.value = { name: m.name, tools, error: '' }
  } catch (e) {
    mcpTestTools.value = { name: m.name, tools: [], error: e.message }
  }
}

async function refreshMcpTools() {
  const f = editingMcp.value
  if (!f || !f.id) return
  mcpMsg.value = ''
  try {
    const tools = await api.adminRefreshMcp(f.id)
    f.tools = tools
    mcpMsg.value = `已刷新，共 ${tools.length} 个工具`
  } catch (e) {
    mcpMsg.value = e.message
  }
}

function toggleBotMcp(mcpId) {
  const arr = editingBot.value.mcp_ids
  const idx = arr.indexOf(mcpId)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(mcpId)
}

function toggleBotSkill(skillId) {
  const arr = editingBot.value.skill_ids
  const idx = arr.indexOf(skillId)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(skillId)
}

async function loadSkills() {
  try {
    skills.value = await api.adminSkills()
    skillMsg.value = ''
  } catch {
    skillMsg.value = '加载技能包失败'
  }
}

function onSkillFile(e) {
  skillUploadFile.value = e.target.files[0] || null
}

async function uploadSkill() {
  if (!skillUploadFile.value) return (skillMsg.value = '请选择技能包文件')
  savingSkill.value = true
  skillMsg.value = ''
  try {
    await api.adminUploadSkill(skillUploadFile.value, skillUploadScope.value, skillUploadEnabled.value ? 1 : 0)
    skillUploadFile.value = null
    skillMsg.value = '上传成功'
    await loadSkills()
  } catch (e) {
    skillMsg.value = e.message
  } finally {
    savingSkill.value = false
  }
}

function openSkillEdit(s) {
  editingSkill.value = {
    id: s.id,
    name: s.name,
    description: s.description || '',
    scope: s.scope,
    enabled: s.enabled,
    user_ids: (s.user_ids || []).slice(),
  }
  if (users.value.length === 0) loadUsers().catch(() => {})
}

function toggleSkillUser(uid) {
  const arr = editingSkill.value.user_ids
  const idx = arr.indexOf(uid)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(uid)
}

async function saveSkill() {
  if (!editingSkill.value) return
  const f = editingSkill.value
  savingSkill.value = true
  skillMsg.value = ''
  try {
    await api.adminUpdateSkill(f.id, {
      name: f.name,
      description: f.description,
      scope: f.scope,
      enabled: f.enabled,
      user_ids: f.scope === 'user' ? f.user_ids : [],
    })
    editingSkill.value = null
    await loadSkills()
  } catch (e) {
    skillMsg.value = e.message
  } finally {
    savingSkill.value = false
  }
}

async function delSkill(s) {
  if (!(await confirmDlg.askConfirm(`删除技能包「${s.name}」？`, { title: '删除技能包', danger: true }))) return
  try {
    await api.adminDeleteSkill(s.id)
    await loadSkills()
  } catch (e) {
    skillMsg.value = e.message
  }
}

function openSkillTest(s) {
  skillTest.value = {
    skill: s,
    tool: s.tools?.[0]?.name || '',
    args: '{}',
    output: '',
    loading: false,
  }
}

async function runSkillTest() {
  const t = skillTest.value
  if (!t) return
  let args = {}
  try {
    args = JSON.parse(t.args || '{}')
  } catch {
    t.output = '参数 JSON 无效'
    return
  }
  t.loading = true
  try {
    const r = await api.adminTestSkill(t.skill.id, t.tool, args)
    t.output = r.output
  } catch (e) {
    t.output = e.message
  } finally {
    t.loading = false
  }
}

async function delUser(u) {
  if (!(await confirmDlg.askConfirm(`删除用户「${u.nickname}」（连同其会话、消息与附件）？`, { title: '删除用户', danger: true }))) return
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

async function loadDingtalk() {
  try {
    const d = await api.adminGetDingtalk()
    dingtalkAppKey.value = d.app_key
    dingtalkAgentId.value = d.agent_id
    dingtalkRedirect.value = d.redirect
    dingtalkSecretSet.value = d.app_secret_set
  } catch {
    dingtalkMsg.value = '加载钉钉配置失败'
  }
}

async function saveDingtalk() {
  savingDingtalk.value = true
  dingtalkMsg.value = ''
  try {
    const body = {
      app_key: dingtalkAppKey.value,
      agent_id: dingtalkAgentId.value,
      redirect: dingtalkRedirect.value,
    }
    if (dingtalkSecret.value) body.app_secret = dingtalkSecret.value
    await api.adminSaveDingtalk(body)
    dingtalkSecret.value = ''
    dingtalkMsg.value = '已保存'
    await loadDingtalk()
  } catch (e) {
    dingtalkMsg.value = e.message
  } finally {
    savingDingtalk.value = false
  }
}

async function loadFeishu() {
  try {
    const d = await api.adminGetFeishu()
    feishuAppId.value = d.app_id
    feishuRedirect.value = d.redirect
    feishuSecretSet.value = d.app_secret_set
  } catch {
    feishuMsg.value = '加载飞书配置失败'
  }
}

async function saveFeishu() {
  savingFeishu.value = true
  feishuMsg.value = ''
  try {
    const body = {
      app_id: feishuAppId.value,
      redirect: feishuRedirect.value,
    }
    if (feishuSecret.value) body.app_secret = feishuSecret.value
    await api.adminSaveFeishu(body)
    feishuSecret.value = ''
    feishuMsg.value = '已保存'
    await loadFeishu()
  } catch (e) {
    feishuMsg.value = e.message
  } finally {
    savingFeishu.value = false
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
  if (!(await confirmDlg.askConfirm('恢复默认 Logo（删除自定义 Logo）？', { title: '恢复默认 Logo' }))) return
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
  if (!(await confirmDlg.askConfirm(`删除接口「${e.name}」？`, { title: '删除接口', danger: true }))) return
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
                <td class="ops">
                  <button class="btn btn-del" @click="delUser(u)">删除</button>
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
                <td class="ops">
                  <button class="btn btn-edit" @click="openEdit(e)">编辑</button>
                  <button class="btn btn-del" @click="del(e)">删除</button>
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

          <div class="card" style="margin-top: 20px">
            <label class="sm-label">防刷验证码
              <select v-model="smsCaptchaProvider" class="input" :disabled="!smsCaptchaEnabled">
                <option v-for="p in captchaProviders" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
            </label>
            <div class="sms-grid" style="margin-top: 8px">
              <label>发送冷却（秒）<input v-model.number="smsCooldown" type="number" min="0" class="input" placeholder="默认 60" /></label>
            </div>
            <div v-if="smsCaptchaProvider === 'geetest'" class="sms-grid">
              <label>极验 captcha_id<input v-model="geetestCaptchaId" class="input" placeholder="极验 v4 应用 ID" /></label>
              <label>极验 captcha_key<input v-model="geetestCaptchaKey" type="password" class="input" :placeholder="geetestKeySet ? '已设置（留空不修改）' : '极验 v4 密钥'" /></label>
            </div>
            <div v-else-if="smsCaptchaProvider === 'tencent'" class="sms-grid">
              <label>腾讯云 CaptchaAppId<input v-model="tencentCaptchaAppId" class="input" placeholder="验证码应用 ID" /></label>
              <label>腾讯云 AppSecretKey<input v-model="tencentCaptchaKey" type="password" class="input" :placeholder="tencentKeySet ? '已设置（留空不修改）' : '验证码密钥'" /></label>
            </div>
            <div v-else-if="smsCaptchaProvider === 'aliyun'" class="sms-grid">
              <label>阿里云 AccessKey ID<input v-model="aliyunCaptchaAccessKeyId" class="input" placeholder="AccessKey ID" /></label>
              <label>阿里云 AccessKey Secret<input v-model="aliyunCaptchaSecret" type="password" class="input" :placeholder="aliyunSecretSet ? '已设置（留空不修改）' : 'AccessKey Secret'" /></label>
              <label>场景 SceneId<input v-model="aliyunSceneId" class="input" placeholder="验证码场景 ID" /></label>
            </div>
            <label class="debug-row" style="margin-top: 12px">
              <input type="checkbox" v-model="smsCaptchaEnabled" /> 发送短信前需要验证码（防刷）
            </label>
            <p class="hint" style="margin-top: 8px">开启后每次发送短信前需完成一次验证码校验；同一手机号在冷却时间内不能重复发送，验证成功后不设限。</p>
            <div class="card-foot">
              <p v-if="captchaMsg" class="hint">{{ captchaMsg }}</p>
              <button class="btn" :disabled="savingCaptcha" @click="saveCaptcha">{{ savingCaptcha ? '保存中…' : '保存防刷设置' }}</button>
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

        <section v-else-if="active === 'mcp'" class="content">
          <div class="head">
            <h2>MCP 工具</h2>
            <button class="btn" @click="openMcpCreate">＋ 添加 MCP 服务</button>
          </div>
          <p v-if="mcpMsg" class="msg">{{ mcpMsg }}</p>
          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>传输</th>
                <th>模式</th>
                <th>工具数</th>
                <th>启用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in mcps" :key="m.id">
                <td>{{ m.name }}</td>
                <td>{{ m.transport === 'stdio' ? 'stdio' : 'HTTP' }}</td>
                <td>{{ m.mode === 'frontend' ? '前端选用' : '大模型选用' }}</td>
                <td>{{ m.tools?.length || 0 }}</td>
                <td>{{ m.enabled ? '✓' : '✕' }}</td>
                <td class="ops">
                  <button class="btn btn-edit" @click="openMcpEdit(m)">编辑</button>
                  <button class="btn btn-test" @click="testMcp(m)">测试</button>
                  <button class="btn btn-del" @click="delMcp(m)">删除</button>
                </td>
              </tr>
              <tr v-if="!mcps.length">
                <td colspan="6" class="empty">暂无 MCP 服务，点击「添加 MCP 服务」创建</td>
              </tr>
            </tbody>
          </table>
          <p class="hint" style="margin-top: 10px">
            MCP（Model Context Protocol）通过工具调用让大模型连接外部服务。HTTP 使用 Streamable HTTP 传输；stdio 在服务端启动本地子进程（配置 command/args/env）。「大模型选用」的工具默认注入、模型自主调用；「前端选用」的工具由用户在聊天页勾选启用。可在企微机器人中配置 MCP，让机器人自动选用。
          </p>
        </section>

        <section v-else-if="active === 'skill'" class="content">
          <div class="head">
            <h2>技能包</h2>
          </div>
          <p v-if="skillMsg" class="msg">{{ skillMsg }}</p>
          <div class="skill-upload">
            <input type="file" accept=".zip,.tar.gz,.tgz" @change="onSkillFile" />
            <select v-model="skillUploadScope" class="input">
              <option v-for="sc in skillScopes" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
            </select>
            <label class="check"><input type="checkbox" v-model="skillUploadEnabled" /> 启用</label>
            <button class="btn" :disabled="savingSkill" @click="uploadSkill">{{ savingSkill ? '上传中…' : '上传技能包' }}</button>
          </div>
          <p class="hint" style="margin-top: 6px">支持 zip / tar.gz，内含 SKILL.md（frontmatter 声明 name/description/tools，正文注入系统提示词）。工具在聊天中被调用时在沙箱中执行。</p>
          <table class="table" style="margin-top: 12px">
            <thead>
              <tr>
                <th>名称</th>
                <th>描述</th>
                <th>可见性</th>
                <th>工具数</th>
                <th>启用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in skills" :key="s.id">
                <td>{{ s.name }}</td>
                <td>{{ s.description || '—' }}</td>
                <td>{{ s.scope === 'user' ? '指定用户' : '全部用户' }}</td>
                <td>{{ s.tools?.length || 0 }}</td>
                <td>{{ s.enabled ? '✓' : '✕' }}</td>
                <td class="ops">
                  <button class="btn btn-edit" @click="openSkillEdit(s)">编辑</button>
                  <button class="btn btn-test" @click="openSkillTest(s)">测试</button>
                  <button class="btn btn-del" @click="delSkill(s)">删除</button>
                </td>
              </tr>
              <tr v-if="!skills.length">
                <td colspan="6" class="empty">暂无技能包，上传一个技能包开始使用</td>
              </tr>
            </tbody>
          </table>
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
                <th>类型</th>
                <th>模式</th>
                <th>数据集ID</th>
                <th>地址</th>
                <th>说明</th>
                <th>启用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="kb in kbs" :key="kb.id">
                <td>{{ kb.name }}</td>
                <td>{{ kb.provider === 'ragflow' ? 'RAGFlow' : 'Dify' }}</td>
                <td>{{ kb.mode === 'llm' ? 'LLM自选' : '前台选择' }}</td>
                <td class="mono">{{ kb.dataset_ids || '—' }}</td>
                <td class="mono">{{ kb.base_url }}</td>
                <td>{{ kb.description || '—' }}</td>
                <td>{{ kb.enabled ? '✓' : '✕' }}</td>
                <td class="ops">
                  <button class="btn btn-edit" @click="openKbEdit(kb)">编辑</button>
                  <button class="btn btn-del" @click="delKb(kb)">删除</button>
                </td>
              </tr>
              <tr v-if="!kbs.length">
                <td colspan="8" class="empty">暂无知识库，点击「添加知识库」创建</td>
              </tr>
            </tbody>
          </table>
          <p class="hint" style="margin-top: 10px">
            知识库仅对接 <strong>Dify</strong> 与 <strong>RAGFlow</strong> 的检索 API。模式：<strong>前台选择</strong>（在聊天界面由用户选用并注入上下文）/ <strong>LLM自选</strong>（作为工具由大模型自主检索，前端无感，企微机器人仅用此模式）。数据集ID支持逗号分隔（Dify 取第一个）。
          </p>
        </section>

        <section v-else-if="active === 'wecom'" class="content">
          <h2>企微设置</h2>

          <h3 class="section-title">基础配置</h3>
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

          <h3 class="section-title">机器人</h3>
          <div class="head">
            <span></span>
            <button class="btn" @click="openBotCreate('wecom')">＋ 添加机器人</button>
          </div>
          <p v-if="botMsg" class="msg">{{ botMsg }}</p>
          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>AgentId</th>
                <th>联网</th>
                <th>知识库</th>
                <th>MCP</th>
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
                <td>{{ b.mcp_ids || '—' }}</td>
                <td>{{ b.enabled ? '✓' : '✕' }}</td>
                <td class="ops">
                  <button class="btn btn-edit" @click="openBotEdit(b)">编辑</button>
                  <button class="btn btn-del" @click="delBot(b)">删除</button>
                </td>
              </tr>
              <tr v-if="!bots.length">
                <td colspan="7" class="empty">暂无机器人，点击「添加机器人」创建</td>
              </tr>
            </tbody>
          </table>
          <p class="hint" style="margin-top: 10px">
            每个机器人对应企微的一个自建应用。请在企微后台为该应用开通「API 接收消息」，回调地址填该机器人的回调 URL（编辑弹窗内显示），并填写 Token 与 EncodingAESKey。创建/编辑后可在弹窗底部看到回调地址。
          </p>
        </section>

        <section v-else-if="active === 'dingtalk'" class="content">
          <h2>钉钉设置</h2>

          <h3 class="section-title">基础配置</h3>
          <div class="card">
            <div class="wecom-grid">
              <label>AppKey<input v-model="dingtalkAppKey" class="input" placeholder="钉钉应用 AppKey（Client ID）" /></label>
              <label>AppSecret<input v-model="dingtalkSecret" type="password" class="input" :placeholder="dingtalkSecretSet ? '已设置（留空不修改）' : '钉钉应用 AppSecret'" /></label>
              <label>AgentId<input v-model="dingtalkAgentId" class="input" placeholder="钉钉应用 AgentId" /></label>
              <label>回调域名<input v-model="dingtalkRedirect" class="input" placeholder="如 https://your.domain" /></label>
            </div>
            <div class="card-foot">
              <p v-if="dingtalkMsg" class="hint">{{ dingtalkMsg }}</p>
              <button class="btn" :disabled="savingDingtalk" @click="saveDingtalk">{{ savingDingtalk ? '保存中…' : '保存钉钉配置' }}</button>
            </div>
          </div>

          <h3 class="section-title">机器人</h3>
          <div class="head">
            <span></span>
            <button class="btn" @click="openBotCreate('dingtalk')">＋ 添加机器人</button>
          </div>
          <p v-if="botMsg" class="msg">{{ botMsg }}</p>
          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>AgentId</th>
                <th>联网</th>
                <th>知识库</th>
                <th>MCP</th>
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
                <td>{{ b.mcp_ids || '—' }}</td>
                <td>{{ b.enabled ? '✓' : '✕' }}</td>
                <td class="ops">
                  <button class="btn btn-edit" @click="openBotEdit(b)">编辑</button>
                  <button class="btn btn-del" @click="delBot(b)">删除</button>
                </td>
              </tr>
              <tr v-if="!bots.length">
                <td colspan="7" class="empty">暂无钉钉机器人，点击「添加机器人」创建</td>
              </tr>
            </tbody>
          </table>
          <p class="hint" style="margin-top: 10px">
            每个钉钉机器人对应钉钉的一个企业内部应用。请在该应用后台开启「消息接收」HTTP 回调，回调地址填该机器人的回调 URL（编辑弹窗内显示），并填写 Token 与 EncodingAESKey。
          </p>
        </section>

        <section v-else-if="active === 'feishu'" class="content">
          <h2>飞书设置</h2>

          <h3 class="section-title">基础配置</h3>
          <div class="card">
            <div class="wecom-grid">
              <label>AppID<input v-model="feishuAppId" class="input" placeholder="飞书应用 AppID（cli_ 开头）" /></label>
              <label>AppSecret<input v-model="feishuSecret" type="password" class="input" :placeholder="feishuSecretSet ? '已设置（留空不修改）' : '飞书应用 AppSecret'" /></label>
              <label>回调域名<input v-model="feishuRedirect" class="input" placeholder="如 https://your.domain" /></label>
            </div>
            <div class="card-foot">
              <p v-if="feishuMsg" class="hint">{{ feishuMsg }}</p>
              <button class="btn" :disabled="savingFeishu" @click="saveFeishu">{{ savingFeishu ? '保存中…' : '保存飞书配置' }}</button>
            </div>
          </div>

          <h3 class="section-title">机器人</h3>
          <div class="head">
            <span></span>
            <button class="btn" @click="openBotCreate('feishu')">＋ 添加机器人</button>
          </div>
          <p v-if="botMsg" class="msg">{{ botMsg }}</p>
          <table class="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>AppID</th>
                <th>联网</th>
                <th>知识库</th>
                <th>MCP</th>
                <th>启用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="b in bots" :key="b.id">
                <td>{{ b.name }}</td>
                <td class="mono">{{ b.corp_id }}</td>
                <td>{{ b.web_search ? '✓' : '✕' }}</td>
                <td>{{ b.kb_ids || '—' }}</td>
                <td>{{ b.mcp_ids || '—' }}</td>
                <td>{{ b.enabled ? '✓' : '✕' }}</td>
                <td class="ops">
                  <button class="btn btn-edit" @click="openBotEdit(b)">编辑</button>
                  <button class="btn btn-del" @click="delBot(b)">删除</button>
                </td>
              </tr>
              <tr v-if="!bots.length">
                <td colspan="7" class="empty">暂无飞书机器人，点击「添加机器人」创建</td>
              </tr>
            </tbody>
          </table>
          <p class="hint" style="margin-top: 10px">
            每个飞书机器人对应飞书的一个自建应用。请在飞书开发者后台开启「机器人」能力并在「事件订阅」中填该机器人的回调 URL（编辑弹窗内显示），订阅 im.message.receive_v1，并按需填写校验 Token 与 EncryptKey。
          </p>
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

          <h3 class="section-title">站点 Logo</h3>
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

    <div v-if="editing" class="modal-mask">
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

    <div v-if="editingKb" class="modal-mask">
      <div class="modal">
        <h3>{{ editingKb.id ? '编辑知识库' : '添加知识库' }}</h3>
        <label>名称<input v-model="editingKb.name" class="input" placeholder="如 内部文档" /></label>
        <div class="form-2">
          <label>类型
            <select v-model="editingKb.provider" class="input">
              <option value="dify">Dify</option>
              <option value="ragflow">RAGFlow</option>
            </select>
          </label>
          <label>使用模式
            <select v-model="editingKb.mode" class="input">
              <option value="frontend">前台选择</option>
              <option value="llm">LLM自选（默认）</option>
            </select>
          </label>
        </div>
        <label>数据集ID<input v-model="editingKb.dataset_ids" class="input" placeholder="如 482b9a…，多个用英文逗号分隔" /></label>
        <label>API 地址<input v-model="editingKb.base_url" class="input" :placeholder="editingKb.provider === 'ragflow' ? '如 http://ragflow-host:9380' : '如 https://api.dify.ai/v1'" /></label>
        <label>API Key<input v-model="editingKb.api_key" type="password" class="input" :placeholder="editingKb.id ? '留空则不修改' : 'Bearer 密钥（Dify 数据集 Key / RAGFlow API Key）'" /></label>
        <label>返回条数（top_k）<input v-model="editingKb.top_k" type="number" class="input" min="1" /></label>
        <label>说明<textarea v-model="editingKb.description" class="input" rows="2" placeholder="知识库简介（可选）"></textarea></label>
        <label class="check"><input type="checkbox" v-model="editingKb.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <div class="kb-test">
          <button class="btn btn-outline" :disabled="testingKb" @click="testKb">{{ testingKb ? '测试中…' : '测试检索' }}</button>
          <span v-if="kbTestResult" class="kb-test-result">{{ kbTestResult }}</span>
        </div>
        <div class="foot">
          <button class="btn btn-outline" @click="editingKb = null">取消</button>
          <button class="btn" :disabled="savingKb" @click="saveKb">{{ savingKb ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="editingBot" class="modal-mask">
      <div class="modal">
        <h3>{{ editingBot.id ? '编辑机器人' : '添加机器人' }}</h3>
        <label>名称<input v-model="editingBot.name" class="input" placeholder="如 客服机器人" /></label>
        <div class="form-2">
          <label>{{ botIsDingtalk ? 'AppKey' : botIsFeishu ? 'AppID' : 'CorpID' }}<input v-model="editingBot.corp_id" class="input" :placeholder="botIsDingtalk ? '钉钉应用 AppKey' : botIsFeishu ? '飞书应用 AppID' : '留空使用企微设置中的 CorpID'" /></label>
          <label>{{ botIsDingtalk ? 'AppSecret' : botIsFeishu ? 'AppSecret' : '应用 Secret' }}<input v-model="editingBot.secret" type="password" class="input" :placeholder="editingBot.id ? '留空不修改' : (botIsDingtalk ? '钉钉应用 AppSecret' : botIsFeishu ? '飞书应用 AppSecret' : '应用 Secret')" /></label>
          <label v-if="!botIsFeishu">AgentId<input v-model="editingBot.agent_id" class="input" :placeholder="botIsDingtalk ? '钉钉应用 AgentId' : '应用 AgentId'" /></label>
          <label>{{ botIsDingtalk || botIsFeishu ? 'URL 验证 Token' : 'Token' }}<input v-model="editingBot.token" type="password" class="input" :placeholder="editingBot.id ? (editingBot.token_masked || '已设置（留空不修改）') : (botIsFeishu ? '校验 Token（选填）' : '回调 Token')" /></label>
          <label>{{ botIsFeishu ? 'EncryptKey' : botIsDingtalk ? 'EncodingAESKey' : 'EncodingAESKey' }}<input v-model="editingBot.aes_key" type="password" class="input" :placeholder="editingBot.id ? '已设置（留空不修改）' : (botIsFeishu ? 'Encrypt Key（选填）' : 'EncodingAESKey')" /></label>
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
        <label>MCP 工具（大模型选用）
          <div class="kb-checkbox-list">
            <label v-for="m in mcps" :key="m.id" class="check">
              <input type="checkbox" :value="m.id" :checked="editingBot.mcp_ids.includes(m.id)" @change="toggleBotMcp(m.id)" />
              {{ m.name }}
            </label>
            <span v-if="!mcps.length" class="hint">暂无 MCP 服务</span>
          </div>
        </label>
        <label>技能包（大模型选用）
          <div class="kb-checkbox-list">
            <label v-for="sk in skills" :key="sk.id" class="check">
              <input type="checkbox" :value="sk.id" :checked="editingBot.skill_ids.includes(sk.id)" @change="toggleBotSkill(sk.id)" />
              {{ sk.name }}
            </label>
            <span v-if="!skills.length" class="hint">暂无技能包</span>
          </div>
        </label>
        <label class="check"><input type="checkbox" v-model="editingBot.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <p v-if="editingBot.id" class="hint" style="margin-top: 8px">
          回调地址：<code>{{ editingBot.callback_url }}</code>
        </p>
        <p v-if="!editingBot.id" class="hint" style="margin-top: 8px">保存后可在此查看回调地址，填入{{ botIsDingtalk ? '钉钉' : botIsFeishu ? '飞书' : '企微' }}后台。</p>
        <div class="foot">
          <button class="btn btn-outline" @click="editingBot = null">取消</button>
          <button class="btn" :disabled="savingBot" @click="saveBot">{{ savingBot ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="editingMcp" class="modal-mask">
      <div class="modal">
        <h3>{{ editingMcp.id ? '编辑 MCP 服务' : '添加 MCP 服务' }}</h3>
        <label>名称<input v-model="editingMcp.name" class="input" placeholder="如 天气服务" /></label>
        <label>说明<textarea v-model="editingMcp.description" class="input" rows="2" placeholder="服务简介（可选）"></textarea></label>
        <label>传输方式
          <select v-model="editingMcp.transport" class="input">
            <option v-for="t in mcpTransports" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </label>
        <template v-if="editingMcp.transport === 'http'">
          <label>服务地址<input v-model="editingMcp.url" class="input" placeholder="如 https://mcp.example/mcp" /></label>
          <label>请求头（JSON）<textarea v-model="editingMcp.headers" class="input mono" rows="2" :placeholder="editingMcp.id ? '已设置（留空不修改）' : '如：Authorization: Bearer xxx'"></textarea></label>
        </template>
        <template v-else>
          <label>命令<input v-model="editingMcp.command" class="input" placeholder="如 npx / uvx" /></label>
          <label>参数（JSON 数组）<textarea v-model="editingMcp.args" class="input mono" rows="2" placeholder='如 ["-y","@modelcontextprotocol/server-xxx"]'></textarea></label>
          <label>环境变量（JSON）<textarea v-model="editingMcp.env" class="input mono" rows="2" placeholder='如 {"API_KEY":"xxx"}'></textarea></label>
        </template>
        <label>选用模式
          <select v-model="editingMcp.mode" class="input">
            <option v-for="mo in mcpModes" :key="mo.value" :value="mo.value">{{ mo.label }}</option>
          </select>
        </label>
        <label class="check"><input type="checkbox" v-model="editingMcp.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <div v-if="editingMcp.tools.length" class="mcp-tools">
          <strong>已发现工具：</strong>
          <ul class="tools-list">
            <li v-for="t in editingMcp.tools" :key="t.name">
              <code>{{ t.name }}</code><span class="hint">{{ t.description || '' }}</span>
            </li>
          </ul>
          <button v-if="editingMcp.id" class="btn btn-outline" @click="refreshMcpTools">刷新工具列表</button>
        </div>
        <div class="foot">
          <button class="btn btn-outline" @click="editingMcp = null">取消</button>
          <button class="btn" :disabled="savingMcp" @click="saveMcp">{{ savingMcp ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="mcpTestTools" class="modal-mask">
      <div class="modal">
        <h3>{{ mcpTestTools.name }} — 工具列表</h3>
        <p v-if="mcpTestTools.error" class="msg">{{ mcpTestTools.error }}</p>
        <ul v-if="mcpTestTools.tools.length" class="tools-list">
          <li v-for="t in mcpTestTools.tools" :key="t.name">
            <code>{{ t.name }}</code><span class="hint">{{ t.description || '' }}</span>
          </li>
        </ul>
        <p v-if="!mcpTestTools.tools.length && !mcpTestTools.error" class="hint">未发现工具</p>
        <div class="foot"><button class="btn" @click="mcpTestTools = null">关闭</button></div>
      </div>
    </div>

    <div v-if="editingSkill" class="modal-mask">
      <div class="modal">
        <h3>编辑技能包</h3>
        <label>名称<input v-model="editingSkill.name" class="input" /></label>
        <label>描述<textarea v-model="editingSkill.description" class="input" rows="2"></textarea></label>
        <label>可见性
          <select v-model="editingSkill.scope" class="input">
            <option v-for="sc in skillScopes" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
          </select>
        </label>
        <template v-if="editingSkill.scope === 'user'">
          <label>分配用户
            <div class="kb-checkbox-list">
              <label v-for="u in users" :key="u.id" class="check">
                <input type="checkbox" :value="u.id" :checked="editingSkill.user_ids.includes(u.id)" @change="toggleSkillUser(u.id)" />
                {{ u.nickname }}
              </label>
              <span v-if="!users.length" class="hint">暂无用户</span>
            </div>
          </label>
        </template>
        <label class="check"><input type="checkbox" v-model="editingSkill.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <div class="foot">
          <button class="btn btn-outline" @click="editingSkill = null">取消</button>
          <button class="btn" :disabled="savingSkill" @click="saveSkill">{{ savingSkill ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="skillTest" class="modal-mask">
      <div class="modal">
        <h3>{{ skillTest.skill.name }} — 试运行工具</h3>
        <label>工具
          <select v-model="skillTest.tool" class="input">
            <option v-for="t in skillTest.skill.tools" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>
        </label>
        <label>参数（JSON）<textarea v-model="skillTest.args" class="input mono" rows="2" placeholder='如 {"file":"a.py"}'></textarea></label>
        <button class="btn" :disabled="skillTest.loading" @click="runSkillTest">{{ skillTest.loading ? '运行中…' : '运行' }}</button>
        <pre v-if="skillTest.output" class="skill-output">{{ skillTest.output }}</pre>
        <div class="foot"><button class="btn" @click="skillTest = null">关闭</button></div>
      </div>
    </div>

    <ConfirmDialog
      :visible="confirmDlg.visible"
      :title="confirmDlg.title"
      :message="confirmDlg.message"
      :danger="confirmDlg.danger"
      @confirm="confirmDlg.confirm"
      @cancel="confirmDlg.cancel"
    />
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
