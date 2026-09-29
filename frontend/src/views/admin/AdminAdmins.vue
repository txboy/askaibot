<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const admins = ref([])
const departments = ref([])
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
    admins.value = await api.adminAdmins()
    departments.value = await api.adminDepartments()
  } catch (e) {
    authGuard(e)
  }
}

function openCreate() {
  editing.value = { id: null, username: '', password: '', role: 'dept', department_id: null }
}

function openEdit(a) {
  editing.value = {
    id: a.id,
    username: a.username,
    password: '',
    role: a.role,
    department_id: a.department_id,
  }
}

async function save() {
  if (!editing.value) return
  const f = editing.value
  if (!f.username || !f.password) return (errorMsg.value = '请输入用户名和初始密码')
  errorMsg.value = ''
  saving.value = true
  try {
    if (f.id) {
      const body = { role: f.role, department_id: f.department_id }
      if (f.password) body.password = f.password
      await api.adminUpdateAdmin(f.id, body)
    } else {
      await api.adminCreateAdmin({ username: f.username, password: f.password, role: f.role, department_id: f.department_id })
    }
    editing.value = null
    await loadAll()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    saving.value = false
  }
}

async function del(a) {
  if (!(await confirmDlg.askConfirm(`删除管理员「${a.username}」？`, { title: '删除管理员', danger: true }))) return
  try {
    await api.adminDeleteAdmin(a.id)
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
      <h2>管理员</h2>
      <button class="btn" @click="openCreate">＋ 新建管理员</button>
    </div>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <table class="table">
      <thead>
        <tr>
          <th>用户名</th>
          <th>角色</th>
          <th>部门</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in admins" :key="a.id">
          <td>{{ a.username }}</td>
          <td>{{ a.role === 'super' ? '超级管理员' : '部门管理员' }}</td>
          <td>{{ a.department_name || '—' }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openEdit(a)">编辑</button>
            <button class="btn btn-del" @click="del(a)">删除</button>
          </td>
        </tr>
        <tr v-if="!admins.length">
          <td colspan="4" class="empty">暂无管理员</td>
        </tr>
      </tbody>
    </table>

    <div v-if="editing" class="modal-mask">
      <div class="modal">
        <h3>{{ editing.id ? '编辑管理员' : '新建管理员' }}</h3>
        <label>用户名
          <input v-model="editing.username" class="input" :disabled="!!editing.id" placeholder="如：dept_manager" />
        </label>
        <label>密码
          <input v-model="editing.password" type="password" class="input" :placeholder="editing.id ? '留空则不修改' : '初始密码'" />
        </label>
        <label>角色
          <select v-model="editing.role" class="input">
            <option value="dept">部门管理员</option>
            <option value="super">超级管理员</option>
          </select>
        </label>
        <label v-if="editing.role === 'dept'">所属部门
          <select v-model="editing.department_id" class="input">
            <option :value="null">未指定</option>
            <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
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
