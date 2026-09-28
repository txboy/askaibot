<script setup>
import { ref, onMounted, watch } from 'vue'
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

const captchaType = ref('')
const captchaImg = ref('')
const captchaId = ref('')
const captchaInput = ref('')
const captchaData = ref({})
const captchaLoading = ref(false)
const cooldownSec = ref(0)
const cooldownTimer = ref(null)
const smsCooldown = ref(60)
const captchaEnabled = ref(false)
const captchaTencentAppId = ref('')
const captchaAliyunScene = ref('')

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

const feishuMode = ref('')
const feishuLoginUrl = ref('')
const feishuQrUrl = ref('')
const feishuEnabled = ref(false)
const inFeishuApp = ref(false)

function detectDingtalk() {
  if (typeof window === 'undefined') return false
  if (window.dd && window.dd.runtime) return true
  const ua = navigator.userAgent || ''
  return /DingTalk/i.test(ua) || /dingtalk/i.test(ua)
}

function detectFeishu() {
  if (typeof window === 'undefined') return false
  if (window.h5 && window.h5.getAuthCode) return true
  if (window.tt && window.tt.requestAuthCode) return true
  const ua = navigator.userAgent || ''
  return /Feishu|Lark/i.test(ua) || /feishu/i.test(ua) || /lark/i.test(ua)
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
    captchaEnabled.value = !!s.captcha_enabled
    smsCooldown.value = s.cooldown || 60
  } catch {}
  try {
    const w = await api.getWecom()
    wecomEnabled.value = !!w.enabled
  } catch {}
  try {
    const d = await api.getDingtalk()
    dingtalkEnabled.value = !!d.enabled
  } catch {}
  try {
    const f = await api.getFeishu()
    feishuEnabled.value = !!f.enabled
  } catch {}
  inDingtalkApp.value = detectDingtalk()
  inFeishuApp.value = detectFeishu()

  if (phoneEnabled.value) tab.value = 'phone'
  else if (wecomEnabled.value) tab.value = 'wecom'
  else if (dingtalkEnabled.value) tab.value = 'dingtalk'
  else if (feishuEnabled.value) tab.value = 'feishu'
  if (tab.value === 'phone' && phoneEnabled.value) loadCaptcha()
  if (!phoneEnabled.value && !wecomEnabled.value && !dingtalkEnabled.value && !feishuEnabled.value) {
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
  if (feishuEnabled.value) {
    try {
      const r = await api.feishuQrcode()
      feishuMode.value = r.mode
      if (r.mode !== 'disabled') {
        feishuLoginUrl.value = r.login_url
        feishuQrUrl.value = await QRCode.toDataURL(r.login_url, { margin: 1, width: 180, color: { dark: '#3b2c22', light: '#ffffff' } })
      }
    } catch (e) {
      msg.value = '加载飞书登录失败: ' + e.message
    }
  }
})

watch(tab, (v) => {
  if (v === 'phone' && phoneEnabled.value) loadCaptcha()
})

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve()
    const s = document.createElement('script')
    s.src = src
    s.onload = resolve
    s.onerror = () => reject(new Error('加载验证码脚本失败'))
    document.head.appendChild(s)
  })
}

async function loadCaptcha() {
  if (!captchaEnabled.value) {
    captchaType.value = ''
    captchaData.value = {}
    return
  }
  captchaLoading.value = true
  captchaData.value = {}
  captchaInput.value = ''
  try {
    const r = await api.captcha()
    captchaType.value = r.type
    if (r.type === 'image') {
      captchaId.value = r.captcha_id
      captchaImg.value = 'data:image/png;base64,' + r.image_base64
    } else if (r.type === 'geetest') {
      await loadScript('https://static.geetest.com/v4/gt4.js')
      if (window.initGeetest4) {
        window.initGeetest4({
          captchaId: r.captcha_id,
          product: 'bind',
          bind: '#gt4-box',
          onSuccess: (obj) => {
            captchaData.value = {
              lot_number: obj.lot_number,
              captcha_output: obj.captcha_output,
              pass_token: obj.pass_token,
              gen_time: obj.gen_time,
            }
          },
        })
      }
    } else if (r.type === 'tencent') {
      captchaTencentAppId.value = r.app_id
      await loadScript('https://turing.captcha.gtimg.com/1/tcaptcha.js')
    } else if (r.type === 'aliyun') {
      captchaAliyunScene.value = r.scene_id
      await loadScript('https://g.alicdn.com/AWSC/AWSC/AWSC.js')
    }
  } catch (e) {
    captchaType.value = ''
  } finally {
    captchaLoading.value = false
  }
}

function openCaptcha() {
  if (!captchaEnabled.value || !captchaType.value) return
  if (captchaType.value === 'geetest') return
  if (captchaType.value === 'tencent' && window.TencentCaptcha) {
    const cap = new window.TencentCaptcha(captchaTencentAppId.value, (res) => {
      if (res.ret === 0) captchaData.value = { ticket: res.ticket, randstr: res.randstr }
    })
    cap.show()
  } else if (captchaType.value === 'aliyun' && window.initAliyunCaptcha) {
    window.initAliyunCaptcha({
      sceneId: captchaAliyunScene.value,
      prefix: captchaAliyunScene.value,
      lang: 'ch',
      success: (res) => {
        captchaData.value = { captcha_verify_param: res.captchaVerifyParam }
      },
    })
  }
}

function startCooldown(seconds) {
  cooldownSec.value = seconds
  if (cooldownTimer.value) clearInterval(cooldownTimer.value)
  cooldownTimer.value = setInterval(() => {
    cooldownSec.value -= 1
    if (cooldownSec.value <= 0) {
      clearInterval(cooldownTimer.value)
      cooldownTimer.value = null
    }
  }, 1000)
}

async function sendCode() {
  if (!phone.value.trim()) return (msg.value = '请输入手机号')
  if (captchaType.value === 'image' && !captchaInput.value.trim()) return (msg.value = '请输入验证码')
  msg.value = ''
  sending.value = true
  try {
    const payload = { phone: phone.value.trim() }
    if (captchaEnabled.value) {
      if (captchaType.value === 'image') {
        payload.captcha_id = captchaId.value
        payload.captcha = captchaInput.value.trim()
      } else {
        Object.assign(payload, captchaData.value || {})
      }
    }
    const r = await api.smsSend(payload)
    debugCode.value = r.debug_code || ''
    msg.value = '验证码已发送'
    startCooldown(smsCooldown.value)
    if (captchaEnabled.value) loadCaptcha()
  } catch (e) {
    msg.value = e.message
    if (captchaEnabled.value) loadCaptcha()
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

function feishuLogin() {
  window.location.href = feishuLoginUrl.value
}

async function feishuFreeLogin() {
  const h5 = window.h5 && window.h5.getAuthCode ? window.h5 : null
  const tt = window.tt && window.tt.requestAuthCode ? window.tt : null
  if (!h5 && !tt) return feishuLogin()
  loggingIn.value = true
  msg.value = ''
  const onSuccess = async (res) => {
    try {
      const code = res.code || res.authCode || ''
      const r = await api.feishuFreeLogin(code)
      store.setAuth(r.token, r.user)
      router.replace('/')
    } catch (e) {
      msg.value = e.message
    } finally {
      loggingIn.value = false
    }
  }
  const onFail = () => {
    loggingIn.value = false
    feishuLogin()
  }
  if (h5) return h5.getAuthCode({ onSuccess, onFail })
  return tt.requestAuthCode({ onSuccess, onFail })
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <Logo class="brand-logo" />
      </div>

      <div class="tabs">
        <button v-if="phoneEnabled" :class="{ active: tab === 'phone' }" @click="tab = 'phone'">手机登录</button>
        <button v-if="wecomEnabled" :class="{ active: tab === 'wecom' }" @click="tab = 'wecom'">企微登录</button>
        <button v-if="dingtalkEnabled" :class="{ active: tab === 'dingtalk' }" @click="tab = 'dingtalk'">钉钉登录</button>
        <button v-if="feishuEnabled" :class="{ active: tab === 'feishu' }" @click="tab = 'feishu'">飞书登录</button>
      </div>

      <div v-if="tab === 'phone' && phoneEnabled" class="panel">
        <div class="phone-row">
          <input v-model="phone" class="input" placeholder="请输入手机号" @keyup.enter="loginPhone" />
          <button class="btn btn-outline code-btn" :disabled="sending || cooldownSec > 0" @click="sendCode">
            {{ sending ? '发送中' : (cooldownSec > 0 ? `重新发送(${cooldownSec}s)` : '获取验证码') }}
          </button>
        </div>

        <div v-if="captchaEnabled && captchaType === 'image'" class="captcha-row">
          <input v-model="captchaInput" class="input" placeholder="验证码" @keyup.enter="sendCode" />
          <img v-if="captchaImg" :src="captchaImg" class="captcha-img" alt="验证码" @click="loadCaptcha" title="点击刷新" />
        </div>
        <div v-else-if="captchaEnabled && captchaType === 'geetest'" class="captcha-row">
          <div id="gt4-box" class="gt4-box"></div>
        </div>
        <div v-else-if="captchaEnabled && captchaType === 'tencent'" class="captcha-row">
          <button class="btn btn-outline" @click="openCaptcha">点击完成腾讯验证</button>
        </div>
        <div v-else-if="captchaEnabled && captchaType === 'aliyun'" class="captcha-row">
          <button class="btn btn-outline" @click="openCaptcha">点击完成阿里云验证</button>
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

      <div v-else-if="tab === 'feishu' && feishuEnabled" class="panel wecom-panel">
        <template v-if="feishuMode === 'disabled'">
          <p class="tip">飞书登录未配置或调试未开启</p>
        </template>
        <template v-else-if="inFeishuApp">
          <p class="tip">检测到飞书环境，使用飞书一键登录</p>
          <button class="btn full" :disabled="loggingIn" @click="feishuFreeLogin">
            {{ loggingIn ? '登录中…' : '飞书一键登录' }}
          </button>
        </template>
        <template v-else>
          <img v-if="feishuQrUrl" :src="feishuQrUrl" class="qr" alt="飞书登录二维码" />
          <p class="tip">{{ feishuMode === 'real' ? '使用飞书授权登录' : '当前为模拟模式，点击下方按钮体验登录' }}</p>
          <button class="btn full" @click="feishuLogin">
            {{ feishuMode === 'real' ? '打开飞书授权' : '模拟扫码登录' }}
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

.captcha-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.captcha-row .input {
  flex: 1;
}

.captcha-img {
  height: 40px;
  width: 120px;
  object-fit: cover;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid var(--border);
  flex-shrink: 0;
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
