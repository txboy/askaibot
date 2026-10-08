<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import UserScopeControl from '../../components/admin/UserScopeControl.vue'

const searchProvider = ref('')
const searchApiKey = ref('')
const searchBaseUrl = ref('')
const searchAuto = ref(false)
const searchApiKeySet = ref(false)
const searchScope = ref('global')
const searchGroupIds = ref([])
const searchMsg = ref('')
const savingSearch = ref(false)
const searchProviders = [
  { value: '', label: '不启用' },
  { value: 'tavily', label: 'Tavily' },
  { value: 'bing', label: 'Bing Web Search' },
  { value: 'searxng', label: 'SearXNG（自托管）' },
  { value: 'duckduckgo', label: 'DuckDuckGo' },
]

async function loadSearch() {
  try {
    const r = await api.adminGetSearch()
    searchProvider.value = r.provider
    searchBaseUrl.value = r.base_url || ''
    searchAuto.value = !!r.auto
    searchApiKeySet.value = r.api_key_set
    searchApiKey.value = ''
    searchScope.value = r.scope || 'global'
    searchGroupIds.value = (r.group_ids || []).slice()
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
      scope: searchScope.value,
      group_ids: searchScope.value === 'group' ? searchGroupIds.value : [],
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

onMounted(loadSearch)
</script>

<template>
  <section class="content">
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
      <UserScopeControl v-model:scope="searchScope" v-model:groups="searchGroupIds" />
      <p class="hint" style="margin-top: 8px">
        开启后，聊天可调用联网搜索补充实时信息。手动开启时用户可在输入框旁点「联网」；自动模式下模型按需自主搜索。Tavily / Bing 需 API Key，SearXNG 需自托管地址，DuckDuckGo 免 Key 但结果有限。
      </p>
      <div class="card-foot">
        <p v-if="searchMsg" class="hint">{{ searchMsg }}</p>
        <button class="btn" :disabled="savingSearch" @click="saveSearch">{{ savingSearch ? '保存中…' : '保存搜索配置' }}</button>
      </div>
    </div>
  </section>
</template>
