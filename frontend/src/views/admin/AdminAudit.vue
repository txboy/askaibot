<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'

const items = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const errorMsg = ref('')
const loading = ref(false)
const filters = ref({ action: '', target_type: '', admin: '' })

function authGuard(e) {
  if (String(e?.message).includes('401') || String(e?.message).includes('管理员')) {
    store.logoutAdmin()
  } else {
    errorMsg.value = e.message
  }
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { page: page.value, size: size.value }
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.target_type) params.target_type = filters.value.target_type
    if (filters.value.admin) params.admin = filters.value.admin
    const r = await api.adminAuditLogs(params)
    items.value = r.items
    total.value = r.total
  } catch (e) {
    authGuard(e)
  } finally {
    loading.value = false
  }
}

async function exportCsv() {
  try {
    const params = {}
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.target_type) params.target_type = filters.value.target_type
    if (filters.value.admin) params.admin = filters.value.admin
    await api.adminAuditExport(params)
  } catch (e) {
    errorMsg.value = e.message
  }
}

const totalPages = () => Math.max(1, Math.ceil(total.value / size.value))

function go(p) {
  page.value = p
  load()
}

onMounted(load)
</script>

<template>
  <section class="content">
    <div class="head">
      <h2>审计日志</h2>
      <button class="btn" @click="exportCsv">导出 CSV</button>
    </div>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <div class="filters">
      <input v-model="filters.admin" class="input" placeholder="操作人" @keyup.enter="load" />
      <input v-model="filters.action" class="input" placeholder="动作，如 user.delete" @keyup.enter="load" />
      <select v-model="filters.target_type" class="input">
        <option value="">全部对象</option>
        <option value="user">用户</option>
        <option value="admin">管理员</option>
        <option value="department">部门</option>
        <option value="endpoint">接口</option>
        <option value="knowledge_base">知识库</option>
        <option value="mcp">MCP</option>
        <option value="skill">技能</option>
        <option value="group">用户组</option>
        <option value="agreement">协议</option>
        <option value="system">系统</option>
        <option value="wecom">企微</option>
        <option value="dingtalk">钉钉</option>
        <option value="feishu">飞书</option>
        <option value="search">搜索</option>
        <option value="sms">短信</option>
        <option value="wecom_bot">机器人</option>
      </select>
      <button class="btn" @click="page = 1; load()">查询</button>
    </div>

    <table class="table">
      <thead>
        <tr>
          <th>时间</th>
          <th>操作人</th>
          <th>角色</th>
          <th>动作</th>
          <th>对象</th>
          <th>摘要</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="it in items" :key="it.id">
          <td class="mono">{{ new Date(it.created_at).toLocaleString() }}</td>
          <td>{{ it.admin_username }}</td>
          <td>{{ it.admin_role }}</td>
          <td class="mono">{{ it.action }}</td>
          <td>{{ it.target_type }}#{{ it.target_id }}</td>
          <td>{{ it.summary }}</td>
        </tr>
        <tr v-if="!items.length && !loading">
          <td colspan="6" class="empty">暂无审计日志</td>
        </tr>
      </tbody>
    </table>

    <div class="pager">
      <button class="btn btn-outline" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
      <span class="hint">第 {{ page }} / {{ totalPages() }} 页 · 共 {{ total }} 条</span>
      <button class="btn btn-outline" :disabled="page >= totalPages()" @click="go(page + 1)">下一页</button>
    </div>
  </section>
</template>

<style scoped>
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.filters .input {
  width: auto;
}
.pager {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}
</style>
