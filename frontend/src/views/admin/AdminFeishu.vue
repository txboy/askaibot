<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import BotManager from './BotManager.vue'

const feishuAppId = ref('')
const feishuSecret = ref('')
const feishuRedirect = ref('')
const feishuSecretSet = ref(false)
const feishuMsg = ref('')
const savingFeishu = ref(false)

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

onMounted(loadFeishu)
</script>

<template>
  <section class="content">
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

    <BotManager provider="feishu" />
  </section>
</template>
