<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'

const dept = ref(null)
const stats = ref(null)
const errorMsg = ref('')

function authGuard(e) {
  if (String(e?.message).includes('401') || String(e?.message).includes('管理员')) {
    store.logoutAdmin()
  } else {
    errorMsg.value = e.message
  }
}

async function load() {
  try {
    dept.value = await api.adminDeptMine()
    stats.value = await api.adminDeptStats()
  } catch (e) {
    authGuard(e)
  }
}

onMounted(load)
</script>

<template>
  <section class="content">
    <h2>本部门用量</h2>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <template v-if="dept">
      <div class="card" style="margin-bottom: 16px">
        <div class="section-title">{{ dept.name }}</div>
        <p class="hint"></p>
        <div class="stats-grid" v-if="stats">
          <div class="stat-card">
            <div class="stat-num">{{ stats.users }}</div>
            <div class="stat-label">成员</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats.conversations }}</div>
            <div class="stat-label">会话</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats.messages }}</div>
            <div class="stat-label">消息</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats.total_tokens }}</div>
            <div class="stat-label">总 Token</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats.today_tokens }}</div>
            <div class="stat-label">今日 Token</div>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
