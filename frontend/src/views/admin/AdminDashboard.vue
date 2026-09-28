<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'

const stats = ref(null)
const endpointsUsage = ref([])

async function loadStats() {
  stats.value = await api.adminStats()
}

async function loadEndpointsUsage() {
  endpointsUsage.value = await api.adminEndpointsUsage()
}

onMounted(() => {
  loadStats()
  loadEndpointsUsage()
})
</script>

<template>
  <section class="content">
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
</template>
