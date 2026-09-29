<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api'
import { applyTheme } from '../../theme'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const confirmDlg = useConfirm()

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

const assistantName = ref('')
const assistantMsg = ref('')
const savingAssistant = ref(false)

const systemPrompt = ref('')
const systemPromptMsg = ref('')
const savingSystemPrompt = ref(false)

const faviconFile = ref(null)
const faviconPreview = ref('')
const faviconSet = ref(false)
const faviconMsg = ref('')
const savingFavicon = ref(false)

const logoFile = ref(null)
const logoPreview = ref('')
const logoSet = ref(false)
const logoMsg = ref('')
const savingLogo = ref(false)

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
    systemPrompt.value = r.system_prompt || ''
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

async function saveSystemPrompt() {
  savingSystemPrompt.value = true
  systemPromptMsg.value = ''
  try {
    await api.adminSaveSystem({ system_prompt: systemPrompt.value })
    systemPromptMsg.value = '已保存'
  } catch (e) {
    systemPromptMsg.value = e.message
  } finally {
    savingSystemPrompt.value = false
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

onMounted(() => {
  loadSystem()
  loadTheme()
  loadDebug()
  loadLogo()
})
</script>

<template>
  <section class="content">
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

    <h3 class="section-title">通用系统提示词</h3>
    <div class="card">
      <label class="sm-label">系统提示词
        <textarea v-model="systemPrompt" class="input" rows="5" placeholder="默认的系统提示词，用于设定助手性格、能力与回复风格。留空则不注入。"></textarea>
      </label>
      <div class="card-foot">
        <p v-if="systemPromptMsg" class="hint">{{ systemPromptMsg }}</p>
        <button class="btn" :disabled="savingSystemPrompt" @click="saveSystemPrompt">{{ savingSystemPrompt ? '保存中…' : '保存提示词' }}</button>
      </div>
      <p class="hint" style="margin-top: 8px">优先级：机器人 &gt; 基础配置（按平台）&gt; 模型接口 &gt; 通用配置。此处为最低优先级，仅在没有更高层级提示词时生效。</p>
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

    <ConfirmDialog
      :visible="confirmDlg.visible"
      :title="confirmDlg.title"
      :message="confirmDlg.message"
      :danger="confirmDlg.danger"
      @confirm="confirmDlg.confirm"
      @cancel="confirmDlg.cancel"
    />
  </section>
</template>
