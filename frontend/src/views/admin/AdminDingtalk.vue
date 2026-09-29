<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import BotManager from './BotManager.vue'
import LoginGuide from '../../components/admin/LoginGuide.vue'

const dingtalkAppKey = ref('')
const dingtalkSecret = ref('')
const dingtalkAgentId = ref('')
const dingtalkRedirect = ref('')
const dingtalkSystemPrompt = ref('')
const dingtalkSecretSet = ref(false)
const dingtalkMsg = ref('')
const savingDingtalk = ref(false)

async function loadDingtalk() {
  try {
    const d = await api.adminGetDingtalk()
    dingtalkAppKey.value = d.app_key
    dingtalkAgentId.value = d.agent_id
    dingtalkRedirect.value = d.redirect
    dingtalkSystemPrompt.value = d.system_prompt || ''
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
      system_prompt: dingtalkSystemPrompt.value,
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

onMounted(loadDingtalk)
</script>

<template>
  <section class="content">
    <h2>钉钉设置</h2>

    <h3 class="section-title">基础配置</h3>
    <div class="card">
      <div class="wecom-grid">
        <label>AppKey<input v-model="dingtalkAppKey" class="input" placeholder="钉钉应用 AppKey（Client ID）" /></label>
        <label>AppSecret<input v-model="dingtalkSecret" type="password" class="input" :placeholder="dingtalkSecretSet ? '已设置（留空不修改）' : '钉钉应用 AppSecret'" /></label>
        <label>AgentId<input v-model="dingtalkAgentId" class="input" placeholder="钉钉应用 AgentId" /></label>
        <label>回调域名<input v-model="dingtalkRedirect" class="input" placeholder="如 https://your.domain" /></label>
      </div>
      <label class="sm-label" style="margin-top: 12px">系统提示词
        <textarea v-model="dingtalkSystemPrompt" class="input" rows="4" placeholder="钉钉基础配置默认提示词；优先级低于机器人提示词。留空则继续向下（模型接口/通用）选择。"></textarea>
      </label>
      <div class="card-foot">
        <p v-if="dingtalkMsg" class="hint">{{ dingtalkMsg }}</p>
        <button class="btn" :disabled="savingDingtalk" @click="saveDingtalk">{{ savingDingtalk ? '保存中…' : '保存钉钉配置' }}</button>
      </div>
    </div>

    <LoginGuide provider="dingtalk" :redirect="dingtalkRedirect" />

    <BotManager provider="dingtalk" />
  </section>
</template>
