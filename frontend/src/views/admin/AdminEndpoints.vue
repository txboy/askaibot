<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'
import UserScopeControl from '../../components/admin/UserScopeControl.vue'

const endpoints = ref([])
const errorMsg = ref('')
const editing = ref(null)
const confirmDlg = useConfirm()

function authGuard(e) {
  if (String(e?.message).includes('401') || String(e?.message).includes('管理员')) {
    store.logoutAdmin()
  } else {
    errorMsg.value = e.message
  }
}

async function loadEndpoints() {
  try {
    endpoints.value = await api.adminEndpoints()
  } catch (e) {
    authGuard(e)
  }
}

function openCreate() {
  editing.value = { name: '', base_url: '', api_key: '', models: '', enabled: 1, is_default: 0, scope: 'global', group_ids: [] }
}

function openEdit(e) {
  editing.value = { id: e.id, name: e.name, base_url: e.base_url, api_key: '', models: e.models, enabled: e.enabled, is_default: e.is_default, scope: e.scope || 'global', group_ids: (e.group_ids || []).slice() }
}

async function save() {
  if (!editing.value) return
  const f = editing.value
  if (!f.name || !f.base_url) return (errorMsg.value = '请填写名称和 base_url')
  errorMsg.value = ''
  try {
    if (f.id) {
      const body = { name: f.name, base_url: f.base_url, models: f.models, enabled: f.enabled, is_default: f.is_default, scope: f.scope, group_ids: f.scope === 'group' ? f.group_ids : [] }
      if (f.api_key) body.api_key = f.api_key
      await api.adminUpdateEndpoint(f.id, body)
    } else {
      await api.adminCreateEndpoint({
        name: f.name,
        base_url: f.base_url,
        api_key: f.api_key,
        models: f.models,
        enabled: f.enabled,
        is_default: f.is_default,
        scope: f.scope,
      })
    }
    editing.value = null
    await loadEndpoints()
  } catch (e) {
    errorMsg.value = e.message
  }
}

async function del(e) {
  if (!(await confirmDlg.askConfirm(`删除接口「${e.name}」？`, { title: '删除接口', danger: true }))) return
  await api.adminDeleteEndpoint(e.id)
  await loadEndpoints()
}

onMounted(loadEndpoints)
</script>

<template>
  <section class="content">
    <div class="head">
      <h2>接口设置</h2>
      <button class="btn" @click="openCreate">＋ 添加接口</button>
    </div>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <table class="table">
      <thead>
        <tr>
          <th>名称</th>
          <th>base_url</th>
          <th>模型</th>
          <th>默认</th>
          <th>启用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in endpoints" :key="e.id">
          <td>{{ e.name }}</td>
          <td class="mono">{{ e.base_url }}</td>
          <td>{{ e.models }}</td>
          <td>{{ e.is_default ? '●' : '' }}</td>
          <td>{{ e.enabled ? '✓' : '✕' }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openEdit(e)">编辑</button>
            <button class="btn btn-del" @click="del(e)">删除</button>
          </td>
        </tr>
        <tr v-if="!endpoints.length">
          <td colspan="6" class="empty">暂无接口，点击「添加接口」创建</td>
        </tr>
      </tbody>
    </table>

    <div v-if="editing" class="modal-mask">
      <div class="modal">
        <h3>{{ editing.id ? '编辑接口' : '添加接口' }}</h3>
        <label>名称<input v-model="editing.name" class="input" placeholder="如 OpenAI" /></label>
        <label>base_url<input v-model="editing.base_url" class="input" placeholder="https://api.openai.com/v1" /></label>
        <label>API Key<input v-model="editing.api_key" type="password" class="input" :placeholder="editing.id ? '留空则不修改' : '请输入 API Key'" /></label>
        <label>模型列表（逗号分隔）<textarea v-model="editing.models" class="input" rows="2" placeholder="gpt-4o, gpt-4o-mini"></textarea></label>
        <label class="check"><input type="checkbox" v-model="editing.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <label class="check"><input type="checkbox" v-model="editing.is_default" :true-value="1" :false-value="0" /> 设为默认接口</label>
        <UserScopeControl v-model:scope="editing.scope" v-model:groups="editing.group_ids" />
        <div class="foot">
          <button class="btn btn-outline" @click="editing = null">取消</button>
          <button class="btn" @click="save">保存</button>
        </div>
      </div>
    </div>

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
