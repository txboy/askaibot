<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import QRCode from 'qrcode'
import { api } from '../api'
import { store } from '../store'
import Logo from '../components/Logo.vue'

const route = useRoute()
const router = useRouter()

const tab = ref('phone')
const phone = ref('')
const code = ref('')
const debugCode = ref('')
const sending = ref(false)
const loggingIn = ref(false)
const msg = ref('')

const wecomMode = ref('')
const wecomLoginUrl = ref('')
const qrUrl = ref('')
const phoneEnabled = ref(false)
const wecomEnabled = ref(false)

const dingtalkMode = ref('')
const dingtalkLoginUrl = ref('')
const dingtalkQrUrl = ref('')
const dingtalkEnabled = ref(false)
const inDingtalkApp = ref(false)
const dingtalkCorpId = ref('')

function detectDingtalk() {
  if (typeof window === 'undefined') return false
  if (window.dd && window.dd.runtime) return true
  const ua = navigator.userAgent || ''
  return /DingTalk/i.test(ua) || /dingtalk/i.test(ua)
}

onMounted(async () => {
  const token = route.query.token
  if (token) {
    store.setAuth(token, {})
    try {
      const user = await api.me()
      store.setAuth(token, user)
    } catch {
      store.logout()
    }
    router.replace('/')
    return
  }
  if (route.query.error) {
    msg.value = String(route.query.error)
  }
  try {
    const s = await api.getSms()
    phoneEnabled.value = !!s.enabled
  } catch {}
  try {
    const w = await api.getWecom()
    wecomEnabled.value = !!w.enabled
  } catch {}
  try {
    const d = await api.getDingtalk()
    dingtalkEnabled.value = !!d.enabled
  } catch {}
  inDingtalkApp.value = detectDingtalk()

  if (phoneEnabled.value) tab.value = 'phone'
  else if (wecomEnabled.value) tab.value = 'wecom'
  else if (dingtalkEnabled.value) tab.value = 'dingtalk'
  if (!phoneEnabled.value && !wecomEnabled.value && !dingtalkEnabled.value) {
    msg.value = '暂无可用登录方式，请联系管理员配置'
    return
  }
  if (wecomEnabled.value) {
    try {
      const r = await api.wecomQrcode()
      wecomMode.value = r.mode
      if (r.mode === 'disabled') {
        wecomLoginUrl.value = ''
        return
      }
      wecomLoginUrl.value = r.login_url
      qrUrl.value = await QRCode.toDataURL(r.login_url, { margin: 1, width: 180, color: { dark: '#3b2c22', light: '#ffffff' } })
    } catch (e) {
      msg.value = '加载企业微信登录失败: ' + e.message
    }
  }
  if (dingtalkEnabled.value) {
    try {
      const r = await api.dingtalkQrcode()
      dingtalkMode.value = r.mode
      if (r.mode !== 'disabled') {
        dingtalkLoginUrl.value = r.login_url
        dingtalkQrUrl.value = await QRCode.toDataURL(r.login_url, { margin: 1, width: 180, color: { dark: '#3b2c22', light: '#ffffff' } })
      }
    } catch (e) {
      msg.value = '加载钉钉登录失败: ' + e.message
    }
  }
})

async function sendCode() {
  if (!phone.value.trim()) return (msg.value = '请输入手机号')
  msg.value = ''
  sending.value = true
  try {
    const r = await api.smsSend(phone.value.trim())
    debugCode.value = r.debug_code || ''
    msg.value = '验证码已发送'
  } catch (e) {
    msg.value = e.message
  } finally {
    sending.value = false
  }
}

async function loginPhone() {
  if (!phone.value.trim() || !code.value.trim()) return (msg.value = '请输入手机号和验证码')
  msg.value = ''
  loggingIn.value = true
  try {
    const r = await api.smsVerify(phone.value.trim(), code.value.trim())
    store.setAuth(r.token, r.user)
    router.replace('/')
  } catch (e) {
    msg.value = e.message
  } finally {
    loggingIn.value = false
  }
}

function wecomLogin() {
  window.location.href = wecomLoginUrl.value
}

function dingtalkLogin() {
  window.location.href = dingtalkLoginUrl.value
}

async function dingtalkFreeLogin() {
  if (!window.dd || !window.dd.runtime || !dingtalkCorpId.value) {
    return dingtalkLogin()
  }
  loggingIn.value = true
  msg.value = ''
  window.dd.runtime.permission.requestAuthCode({
    corpId: dingtalkCorpId.value,
    onSuccess: async (res) => {
      try {
        const r = await api.dingtalkFreeLogin(res.code)
        store.setAuth(r.token, r.user)
        router.replace('/')
      } catch (e) {
        msg.value = e.message
      } finally {
        loggingIn.value = false
      }
    },
    onFail: () => {
      loggingIn.value = false
      dingtalkLogin()
    },
  })
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <Logo class="brand-logo" />
      </div>

      <div class="tabs">
        <button v-if="phoneEnabled" :class="{ active: tab === 'phone' }" @click="tab = 'phone'">手机号登录</button>
        <button v-if="wecomEnabled" :class="{ active: tab === 'wecom' }" @click="tab = 'wecom'">企业微信登录</button>
        <button v-if="dingtalkEnabled" :class="{ active: tab === 'dingtalk' }" @click="tab = 'dingtalk'">钉钉登录</button>
      </div>

      <div v-if="tab === 'phone' && phoneEnabled" class="panel">
        <div class="phone-row">
          <input v-model="phone" class="input" placeholder="请输入手机号" @keyup.enter="loginPhone" />
          <button class="btn btn-outline code-btn" :disabled="sending" @click="sendCode">
            {{ sending ? '发送中' : '获取验证码' }}
          </button>
        </div>
        <p v-if="debugCode" class="debug">模拟验证码：<b>{{ debugCode }}</b></p>
        <input v-model="code" class="input" placeholder="请输入验证码" @keyup.enter="loginPhone" />
        <button class="btn full" :disabled="loggingIn" @click="loginPhone">
          {{ loggingIn ? '登录中…' : '登录' }}
        </button>
      </div>

      <div v-else-if="tab === 'wecom' && wecomEnabled" class="panel wecom-panel">
        <template v-if="wecomMode === 'disabled'">
          <p class="tip">企业微信登录未配置或调试未开启</p>
        </template>
        <template v-else>
          <img v-if="qrUrl" :src="qrUrl" class="qr" alt="企业微信登录二维码" />
          <p class="tip">{{ wecomMode === 'real' ? '使用企业微信扫码登录' : '当前为模拟模式，点击下方按钮体验登录' }}</p>
          <button class="btn full" @click="wecomLogin">
            {{ wecomMode === 'real' ? '打开企业微信授权' : '模拟扫码登录' }}
          </button>
        </template>
      </div>

      <div v-else-if="tab === 'dingtalk' && dingtalkEnabled" class="panel wecom-panel">
        <template v-if="dingtalkMode === 'disabled'">
          <p class="tip">钉钉登录未配置或调试未开启</p>
        </template>
        <template v-else-if="inDingtalkApp">
          <p class="tip">检测到钉钉环境，使用钉钉一键登录</p>
          <button class="btn full" :disabled="loggingIn" @click="dingtalkFreeLogin">
            {{ loggingIn ? '登录中…' : '钉钉一键登录' }}
          </button>
        </template>
        <template v-else>
          <img v-if="dingtalkQrUrl" :src="dingtalkQrUrl" class="qr" alt="钉钉登录二维码" />
          <p class="tip">{{ dingtalkMode === 'real' ? '使用钉钉扫一扫登录' : '当前为模拟模式，点击下方按钮体验登录' }}</p>
          <button class="btn full" @click="dingtalkLogin">
            {{ dingtalkMode === 'real' ? '打开钉钉授权' : '模拟扫码登录' }}
          </button>
        </template>
      </div>

      <p v-if="msg" class="msg">{{ msg }}</p>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 30% 20%, var(--surface-soft), var(--bg));
}

.login-card {
  width: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 32px 28px;
  box-shadow: var(--shadow);
}

.brand {
  text-align: center;
  margin-bottom: 24px;
}

.brand-logo {
  width: 220px;
  margin: 0 auto 10px;
}

.tabs {
  display: flex;
  gap: 8px;
  background: var(--bg-sidebar);
  padding: 4px;
  border-radius: 10px;
  margin-bottom: 18px;
}

.tabs button {
  flex: 1;
  padding: 8px;
  border-radius: 8px;
  color: var(--text-muted);
}

.tabs button.active {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow);
}

.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.phone-row {
  display: flex;
  gap: 8px;
}

.phone-row .input {
  flex: 1;
}

.code-btn {
  white-space: nowrap;
}

.debug {
  font-size: 13px;
  color: var(--primary);
}

.full {
  width: 100%;
  margin-top: 4px;
}

.wecom-panel {
  align-items: center;
  text-align: center;
}

.qr {
  width: 180px;
  height: 180px;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.tip {
  font-size: 13px;
  color: var(--text-muted);
}

.msg {
  width: 100%;
  margin-top: 12px;
  font-size: 13px;
  color: var(--danger);
  text-align: center;
}


</style>
