<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import BotManager from './BotManager.vue'

const wecomCorpId = ref('')
const wecomSecret = ref('')
const wecomAgentId = ref('')
const wecomRedirect = ref('')
const wecomSecretSet = ref(false)
const wecomMsg = ref('')
const savingWecom = ref(false)

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

onMounted(loadWecom)
</script>

<template>
  <section class="content">
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

    <BotManager provider="wecom" />
  </section>
</template>
