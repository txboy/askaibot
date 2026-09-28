<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { store } from '../../store'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const groups = ref([])
const users = ref([])
const endpoints = ref([])
const kbs = ref([])
const mcps = ref([])
const skills = ref([])
const errorMsg = ref('')
const editing = ref(null)
const saving = ref(false)
const confirmDlg = useConfirm()

const resourceTypes = [
  { key: 'endpoint', label: '接口', items: endpoints },
  { key: 'knowledge_base', label: '知识库', items: kbs },
  { key: 'mcp', label: 'MCP 工具', items: mcps },
  { key: 'skill', label: '技能包', items: skills },
]

function authGuard(e) {
  if (String(e?.message).includes('401') || String(e?.message).includes('管理员')) {
    store.logoutAdmin()
  } else {
    errorMsg.value = e.message
  }
}

async function loadAll() {
  try {
    groups.value = await api.adminGroups()
    users.value = await api.adminUsers()
    endpoints.value = await api.adminEndpoints()
    kbs.value = await api.adminGetKnowledgeBases()
    mcps.value = await api.adminMcpServers()
    skills.value = await api.adminSkills()
  } catch (e) {
    authGuard(e)
  }
}

function openCreate() {
  editing.value = {
    id: null,
    name: '',
    description: '',
    member_ids: [],
    grants: { endpoint: [], knowledge_base: [], mcp: [], search: [], skill: [] },
  }
}

function openEdit(g) {
  editing.value = {
    id: g.id,
    name: g.name,
    description: g.description,
    member_ids: (g.member_ids || []).slice(),
    grants: {
      endpoint: [...(g.grants?.endpoint || [])],
      knowledge_base: [...(g.grants?.knowledge_base || [])],
      mcp: [...(g.grants?.mcp || [])],
      search: [...(g.grants?.search || [])],
      skill: [...(g.grants?.skill || [])],
    },
  }
}

function toggleMember(uid) {
  const arr = editing.value.member_ids
  const idx = arr.indexOf(uid)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(uid)
}

function toggleGrant(type, id) {
  const arr = editing.value.grants[type]
  const idx = arr.indexOf(id)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(id)
}

function toggleSearch() {
  const arr = editing.value.grants.search
  const idx = arr.indexOf(0)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(0)
}

async function save() {
  if (!editing.value) return
  const f = editing.value
  if (!f.name) return (errorMsg.value = '请输入组名')
  errorMsg.value = ''
  saving.value = true
  try {
    const body = {
      name: f.name,
      description: f.description,
      member_ids: f.member_ids,
      grants: f.grants,
    }
    if (f.id) await api.adminUpdateGroup(f.id, body)
    else await api.adminCreateGroup(body)
    editing.value = null
    await loadAll()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    saving.value = false
  }
}

async function del(g) {
  if (!(await confirmDlg.askConfirm(`删除用户组「${g.name}」？`, { title: '删除用户组', danger: true }))) return
  try {
    await api.adminDeleteGroup(g.id)
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
      <h2>用户组</h2>
      <button class="btn" @click="openCreate">＋ 新建用户组</button>
    </div>
    <p v-if="errorMsg" class="msg">{{ errorMsg }}</p>

    <table class="table">
      <thead>
        <tr>
          <th>名称</th>
          <th>描述</th>
          <th>成员数</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="g in groups" :key="g.id">
          <td>{{ g.name }}</td>
          <td>{{ g.description || '—' }}</td>
          <td>{{ g.member_count }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openEdit(g)">编辑</button>
            <button class="btn btn-del" @click="del(g)">删除</button>
          </td>
        </tr>
        <tr v-if="!groups.length">
          <td colspan="4" class="empty">暂无用户组，点击「新建用户组」创建</td>
        </tr>
      </tbody>
    </table>

    <div v-if="editing" class="modal-mask">
      <div class="modal" style="max-width: 560px; max-height: 90vh; overflow-y: auto">
        <h3>{{ editing.id ? '编辑用户组' : '新建用户组' }}</h3>
        <label>组名<input v-model="editing.name" class="input" placeholder="如：研发组" /></label>
        <label>描述<textarea v-model="editing.description" class="input" rows="2"></textarea></label>

        <label>组成员
          <div class="kb-checkbox-list">
            <label v-for="u in users" :key="u.id" class="check">
              <input type="checkbox" :value="u.id" :checked="editing.member_ids.includes(u.id)" @change="toggleMember(u.id)" />
              {{ u.nickname }}{{ u.phone ? `（${u.phone}）` : '' }}
            </label>
            <span v-if="!users.length" class="hint">暂无用户</span>
          </div>
        </label>

        <template v-for="rt in resourceTypes" :key="rt.key">
          <label class="section-title">{{ rt.label }}授权
            <div class="kb-checkbox-list">
              <label v-for="it in rt.items" :key="it.id" class="check">
                <input type="checkbox" :value="it.id" :checked="editing.grants[rt.key].includes(it.id)" @change="toggleGrant(rt.key, it.id)" />
                {{ it.name }}
              </label>
              <span v-if="!rt.items.length" class="hint">暂无{{ rt.label }}</span>
            </div>
          </label>
        </template>

        <label class="section-title">联网搜索
          <label class="check">
            <input type="checkbox" :checked="editing.grants.search.includes(0)" @change="toggleSearch" />
            允许本组使用联网搜索
          </label>
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
