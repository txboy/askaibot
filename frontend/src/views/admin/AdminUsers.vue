<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const users = ref([])
const errorMsg = ref('')
const confirmDlg = useConfirm()

function authGuard(e) {
  if (String(e?.message).includes('401') || String(e?.message).includes('管理员')) {
    store.logoutAdmin()
  } else {
    errorMsg.value = e.message
  }
}

async function loadUsers() {
  try {
    users.value = await api.adminUsers()
  } catch (e) {
    authGuard(e)
  }
}

async function delUser(u) {
  if (!(await confirmDlg.askConfirm(`删除用户「${u.nickname}」（连同其会话、消息与附件）？`, { title: '删除用户', danger: true }))) return
  try {
    await api.adminDeleteUser(u.id)
    await loadUsers()
  } catch (e) {
    errorMsg.value = e.message
  }
}

function fmtDate(s) {
  if (!s) return '—'
  return String(s).replace('T', ' ').slice(0, 16)
}

const PLATFORM_NAMES = {
  wecom: '企业微信',
  dingtalk: '钉钉',
  feishu: '飞书',
  phone: '手机号',
}

function platformName(p) {
  return PLATFORM_NAMES[p] || '—'
}

onMounted(loadUsers)
</script>

<template>
  <section class="content">
    <div class="head">
      <h2>用户列表</h2>
      <button class="btn btn-outline" @click="loadUsers">刷新</button>
    </div>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <table class="table">
      <thead>
        <tr>
          <th>昵称</th>
          <th>平台</th>
          <th>手机号</th>
          <th>会话数</th>
          <th>总 Token</th>
          <th>当天 Token</th>
          <th>注册时间</th>
          <th>最近活跃</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.nickname }}</td>
          <td>{{ platformName(u.platform) }}</td>
          <td>{{ u.phone || '—' }}</td>
          <td>{{ u.conversation_count }}</td>
          <td>{{ u.total_tokens }}</td>
          <td>{{ u.today_tokens }}</td>
          <td>{{ fmtDate(u.created_at) }}</td>
          <td>{{ fmtDate(u.last_active) }}</td>
          <td class="ops">
            <button class="btn btn-del" @click="delUser(u)">删除</button>
          </td>
        </tr>
        <tr v-if="!users.length">
          <td colspan="9" class="empty">暂无用户</td>
        </tr>
      </tbody>
    </table>

    <ConfirmDialog
      :visible="confirmDlg.visible"
      :title="confirmDlg.title"
      :message="confirmDlg.message"
      :danger="confirmDlg.danger"
      @confirm="confirmDlg.confirm"
      @cancel="confirmDlg.cancel"
    />
  </section>
</template>
