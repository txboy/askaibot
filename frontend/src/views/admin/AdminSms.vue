<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'

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

onMounted(loadSms)
</script>

<template>
  <section class="content">
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
</template>
