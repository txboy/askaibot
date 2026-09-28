<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const skills = ref([])
const skillMsg = ref('')
const savingSkill = ref(false)
const editingSkill = ref(null)
const skillTest = ref(null)
const skillUploadFile = ref(null)
const skillUploadScope = ref('global')
const skillUploadEnabled = ref(true)
const users = ref([])
const confirmDlg = useConfirm()
const skillScopes = [
  { value: 'global', label: '全部用户' },
  { value: 'user', label: '指定用户' },
]

async function loadSkills() {
  try {
    skills.value = await api.adminSkills()
    skillMsg.value = ''
  } catch {
    skillMsg.value = '加载技能包失败'
  }
}

function onSkillFile(e) {
  skillUploadFile.value = e.target.files[0] || null
}

async function uploadSkill() {
  if (!skillUploadFile.value) return (skillMsg.value = '请选择技能包文件')
  savingSkill.value = true
  skillMsg.value = ''
  try {
    await api.adminUploadSkill(skillUploadFile.value, skillUploadScope.value, skillUploadEnabled.value ? 1 : 0)
    skillUploadFile.value = null
    skillMsg.value = '上传成功'
    await loadSkills()
  } catch (e) {
    skillMsg.value = e.message
  } finally {
    savingSkill.value = false
  }
}

function openSkillEdit(s) {
  editingSkill.value = {
    id: s.id,
    name: s.name,
    description: s.description || '',
    scope: s.scope,
    enabled: s.enabled,
    user_ids: (s.user_ids || []).slice(),
  }
  if (users.value.length === 0) api.adminUsers().then((u) => (users.value = u)).catch(() => {})
}

function toggleSkillUser(uid) {
  const arr = editingSkill.value.user_ids
  const idx = arr.indexOf(uid)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(uid)
}

async function saveSkill() {
  if (!editingSkill.value) return
  const f = editingSkill.value
  savingSkill.value = true
  skillMsg.value = ''
  try {
    await api.adminUpdateSkill(f.id, {
      name: f.name,
      description: f.description,
      scope: f.scope,
      enabled: f.enabled,
      user_ids: f.scope === 'user' ? f.user_ids : [],
    })
    editingSkill.value = null
    await loadSkills()
  } catch (e) {
    skillMsg.value = e.message
  } finally {
    savingSkill.value = false
  }
}

async function delSkill(s) {
  if (!(await confirmDlg.askConfirm(`删除技能包「${s.name}」？`, { title: '删除技能包', danger: true }))) return
  try {
    await api.adminDeleteSkill(s.id)
    await loadSkills()
  } catch (e) {
    skillMsg.value = e.message
  }
}

function openSkillTest(s) {
  skillTest.value = {
    skill: s,
    tool: s.tools?.[0]?.name || '',
    args: '{}',
    output: '',
    loading: false,
  }
}

async function runSkillTest() {
  const t = skillTest.value
  if (!t) return
  let args = {}
  try {
    args = JSON.parse(t.args || '{}')
  } catch {
    t.output = '参数 JSON 无效'
    return
  }
  t.loading = true
  try {
    const r = await api.adminTestSkill(t.skill.id, t.tool, args)
    t.output = r.output
  } catch (e) {
    t.output = e.message
  } finally {
    t.loading = false
  }
}

onMounted(loadSkills)
</script>

<template>
  <section class="content">
    <div class="head">
      <h2>技能包</h2>
    </div>
    <p v-if="skillMsg" class="msg">{{ skillMsg }}</p>
    <div class="skill-upload">
      <input type="file" accept=".zip,.tar.gz,.tgz" @change="onSkillFile" />
      <select v-model="skillUploadScope" class="input">
        <option v-for="sc in skillScopes" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
      </select>
      <label class="check"><input type="checkbox" v-model="skillUploadEnabled" /> 启用</label>
      <button class="btn" :disabled="savingSkill" @click="uploadSkill">{{ savingSkill ? '上传中…' : '上传技能包' }}</button>
    </div>
    <p class="hint" style="margin-top: 6px">支持 zip / tar.gz，内含 SKILL.md（frontmatter 声明 name/description/tools，正文注入系统提示词）。工具在聊天中被调用时在沙箱中执行。</p>
    <table class="table" style="margin-top: 12px">
      <thead>
        <tr>
          <th>名称</th>
          <th>描述</th>
          <th>可见性</th>
          <th>工具数</th>
          <th>启用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in skills" :key="s.id">
          <td>{{ s.name }}</td>
          <td>{{ s.description || '—' }}</td>
          <td>{{ s.scope === 'user' ? '指定用户' : '全部用户' }}</td>
          <td>{{ s.tools?.length || 0 }}</td>
          <td>{{ s.enabled ? '✓' : '✕' }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openSkillEdit(s)">编辑</button>
            <button class="btn btn-test" @click="openSkillTest(s)">测试</button>
            <button class="btn btn-del" @click="delSkill(s)">删除</button>
          </td>
        </tr>
        <tr v-if="!skills.length">
          <td colspan="6" class="empty">暂无技能包，上传一个技能包开始使用</td>
        </tr>
      </tbody>
    </table>

    <div v-if="editingSkill" class="modal-mask">
      <div class="modal">
        <h3>编辑技能包</h3>
        <label>名称<input v-model="editingSkill.name" class="input" /></label>
        <label>描述<textarea v-model="editingSkill.description" class="input" rows="2"></textarea></label>
        <label>可见性
          <select v-model="editingSkill.scope" class="input">
            <option v-for="sc in skillScopes" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
          </select>
        </label>
        <template v-if="editingSkill.scope === 'user'">
          <label>分配用户
            <div class="kb-checkbox-list">
              <label v-for="u in users" :key="u.id" class="check">
                <input type="checkbox" :value="u.id" :checked="editingSkill.user_ids.includes(u.id)" @change="toggleSkillUser(u.id)" />
                {{ u.nickname }}
              </label>
              <span v-if="!users.length" class="hint">暂无用户</span>
            </div>
          </label>
        </template>
        <label class="check"><input type="checkbox" v-model="editingSkill.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <div class="foot">
          <button class="btn btn-outline" @click="editingSkill = null">取消</button>
          <button class="btn" :disabled="savingSkill" @click="saveSkill">{{ savingSkill ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="skillTest" class="modal-mask">
      <div class="modal">
        <h3>{{ skillTest.skill.name }} — 试运行工具</h3>
        <label>工具
          <select v-model="skillTest.tool" class="input">
            <option v-for="t in skillTest.skill.tools" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>
        </label>
        <label>参数（JSON）<textarea v-model="skillTest.args" class="input mono" rows="2" placeholder='如 {"file":"a.py"}'></textarea></label>
        <button class="btn" :disabled="skillTest.loading" @click="runSkillTest">{{ skillTest.loading ? '运行中…' : '运行' }}</button>
        <pre v-if="skillTest.output" class="skill-output">{{ skillTest.output }}</pre>
        <div class="foot"><button class="btn" @click="skillTest = null">关闭</button></div>
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
