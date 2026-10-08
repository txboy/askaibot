<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const departments = ref([])
const admins = ref([])
const users = ref([])
const errorMsg = ref('')
const editing = ref(null)
const assign = ref(null)
const adminAssign = ref(null)
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
    departments.value = await api.adminDepartments()
    admins.value = await api.adminAdmins()
    users.value = await api.adminUsers()
  } catch (e) {
    authGuard(e)
  }
}

function openCreate() {
  editing.value = { id: null, name: '', description: '', token_limit_daily: 0 }
}

function openEdit(d) {
  editing.value = { id: d.id, name: d.name, description: d.description, token_limit_daily: d.token_limit_daily ?? 0 }
}

async function save() {
  if (!editing.value) return
  const f = editing.value
  if (!f.name) return (errorMsg.value = '请输入部门名称')
  errorMsg.value = ''
  saving.value = true
  try {
    const body = { name: f.name, description: f.description || '', token_limit_daily: Number(f.token_limit_daily) || 0 }
    if (f.id) await api.adminUpdateDepartment(f.id, body)
    else await api.adminCreateDepartment(body)
    editing.value = null
    await loadAll()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    saving.value = false
  }
}

function openAdminAssign(d) {
  adminAssign.value = { department_id: d.id, name: d.name, admin_id: null }
}

async function saveAdminAssign() {
  if (!adminAssign.value) return
  try {
    await api.adminSetDeptAdmin(adminAssign.value.department_id, adminAssign.value.admin_id || null)
    adminAssign.value = null
    await loadAll()
  } catch (e) {
    errorMsg.value = e.message
  }
}

function openAssign(d) {
  assign.value = { department_id: d.id, name: d.name }
}

async function saveAssign() {
  if (!assign.value) return
  try {
    await api.adminAssignUserDept(assign.value.user_id, assign.value.department_id)
    assign.value = null
    await loadAll()
  } catch (e) {
    errorMsg.value = e.message
  }
}

async function del(d) {
  if (!(await confirmDlg.askConfirm(`删除部门「${d.name}」？成员将变为未分配。`, { title: '删除部门', danger: true }))) return
  try {
    await api.adminDeleteDepartment(d.id)
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
      <h2>部门管理</h2>
      <button class="btn" @click="openCreate">＋ 新建部门</button>
    </div>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <table class="table">
      <thead>
        <tr>
          <th>名称</th>
          <th>描述</th>
          <th>成员数</th>
          <th>管理员</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in departments" :key="d.id">
          <td>{{ d.name }}</td>
          <td>{{ d.description || '—' }}</td>
          <td>{{ d.member_count }}</td>
          <td>{{ d.admin_username || '未指定' }}</td>
          <td class="ops">
            <button class="btn btn-outline" @click="openAdminAssign(d)">指派管理员</button>
            <button class="btn btn-outline" @click="openAssign(d)">分配用户</button>
            <button class="btn btn-edit" @click="openEdit(d)">编辑</button>
            <button class="btn btn-del" @click="del(d)">删除</button>
          </td>
        </tr>
        <tr v-if="!departments.length">
          <td colspan="5" class="empty">暂无部门，点击「新建部门」创建</td>
        </tr>
      </tbody>
    </table>

    <div v-if="editing" class="modal-mask">
      <div class="modal">
        <h3>{{ editing.id ? '编辑部门' : '新建部门' }}</h3>
        <label>部门名称<input v-model="editing.name" class="input" placeholder="如：研发部" /></label>
        <label>描述<textarea v-model="editing.description" class="input" rows="2"></textarea></label>
        <label>每日 Token 限额<input v-model.number="editing.token_limit_daily" class="input" type="number" min="0" placeholder="0 表示不限" /></label>
        <div class="foot">
          <button class="btn btn-outline" @click="editing = null">取消</button>
          <button class="btn" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="assign" class="modal-mask">
      <div class="modal">
        <h3>分配用户到「{{ assign.name }}」</h3>
        <p class="hint">选择一位用户：</p>
        <select v-model="assign.user_id" class="input">
          <option :value="null" disabled>请选择用户</option>
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.nickname }}{{ u.phone ? `（${u.phone}）` : '' }}</option>
        </select>
        <div class="foot">
          <button class="btn btn-outline" @click="assign = null">取消</button>
          <button class="btn" @click="saveAssign">分配</button>
        </div>
      </div>
    </div>

    <div v-if="adminAssign" class="modal-mask">
      <div class="modal">
        <h3>指派「{{ adminAssign.name }}」管理员</h3>
        <p class="hint">选择一个部门管理员账号：</p>
        <select v-model="adminAssign.admin_id" class="input">
          <option :value="null">清除管理员</option>
          <option v-for="a in admins" :key="a.id" :value="a.id">{{ a.username }}（{{ a.role }}）</option>
        </select>
        <div class="foot">
          <button class="btn btn-outline" @click="adminAssign = null">取消</button>
          <button class="btn" @click="saveAdminAssign">保存</button>
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
