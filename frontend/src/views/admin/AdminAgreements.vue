<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const agreements = ref([])
const errorMsg = ref('')
const editing = ref(null)
const saving = ref(false)
const confirmDlg = useConfirm()

function authGuard(e) {
  if (String(e?.message).includes('401') || String(e?.message).includes('管理员')) {
    store.logoutAdmin()
  } else {
    errorMsg.value = e.message
  }
}

async function loadAll() {
  try {
    agreements.value = await api.adminAgreements()
  } catch (e) {
    authGuard(e)
  }
}

function openCreate() {
  editing.value = {
    id: null,
    title: '',
    content: '',
    required: 1,
    enabled: 1,
  }
}

function openEdit(a) {
  editing.value = {
    id: a.id,
    title: a.title,
    content: a.content,
    required: a.required,
    enabled: a.enabled,
  }
}

async function save() {
  if (!editing.value) return
  const f = editing.value
  if (!f.title.trim()) return (errorMsg.value = '请输入协议标题')
  errorMsg.value = ''
  saving.value = true
  try {
    const body = {
      title: f.title,
      content: f.content,
      required: f.required ? 1 : 0,
      enabled: f.enabled ? 1 : 0,
    }
    if (f.id) await api.adminUpdateAgreement(f.id, body)
    else await api.adminCreateAgreement(body)
    editing.value = null
    await loadAll()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    saving.value = false
  }
}

async function del(a) {
  if (!(await confirmDlg.askConfirm(`删除协议「${a.title}」？`, { title: '删除协议', danger: true }))) return
  try {
    await api.adminDeleteAgreement(a.id)
    await loadAll()
  } catch (e) {
    errorMsg.value = e.message
  }
}

onMounted(loadAll)
</script>

<template>
  <section class="content">
    <div class="head">
      <h2>协议管理</h2>
      <button class="btn" @click="openCreate">＋ 新建协议</button>
    </div>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <table class="table">
      <thead>
        <tr>
          <th>标题</th>
          <th>内容</th>
          <th>必须确认</th>
          <th>启用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in agreements" :key="a.id">
          <td>{{ a.title }}</td>
          <td class="agree-preview">{{ a.content || '—' }}</td>
          <td>{{ a.required ? '是' : '否' }}</td>
          <td>{{ a.enabled ? '是' : '否' }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openEdit(a)">编辑</button>
            <button class="btn btn-del" @click="del(a)">删除</button>
          </td>
        </tr>
        <tr v-if="!agreements.length">
          <td colspan="5" class="empty">暂无协议，点击「新建协议」创建</td>
        </tr>
      </tbody>
    </table>

    <div v-if="editing" class="modal-mask">
      <div class="modal" style="max-width: 560px; max-height: 90vh; overflow-y: auto">
        <h3>{{ editing.id ? '编辑协议' : '新建协议' }}</h3>
        <label>标题<input v-model="editing.title" class="input" placeholder="如：用户协议" /></label>
        <label>内容<textarea v-model="editing.content" class="input" rows="10" placeholder="请输入协议正文"></textarea></label>
        <label class="check">
          <input type="checkbox" v-model="editing.required" :true-value="1" :false-value="0" />
          必须确认（登录前需勾选同意）
        </label>
        <label class="check">
          <input type="checkbox" v-model="editing.enabled" :true-value="1" :false-value="0" />
          启用
        </label>

        <div class="foot">
          <button class="btn btn-outline" @click="editing = null">取消</button>
          <button class="btn" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
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

<style scoped>
.agree-preview {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.check {
  flex-direction: row !important;
  align-items: center;
  gap: 8px !important;
  font-size: 13px;
  color: var(--text);
}
</style>
