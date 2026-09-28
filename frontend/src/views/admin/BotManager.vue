<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const props = defineProps({
  provider: { type: String, default: 'wecom' },
})

const bots = ref([])
const botMsg = ref('')
const savingBot = ref(false)
const editingBot = ref(null)
const endpoints = ref([])
const kbs = ref([])
const mcps = ref([])
const skills = ref([])
const confirmDlg = useConfirm()

const isDingtalk = computed(() => props.provider === 'dingtalk')
const isFeishu = computed(() => props.provider === 'feishu')
const idLabel = computed(() => (isFeishu.value ? 'AppID' : 'AgentId'))
const emptyText = computed(() =>
  isFeishu.value ? '暂无飞书机器人，点击「添加机器人」创建' : isDingtalk.value ? '暂无钉钉机器人，点击「添加机器人」创建' : '暂无机器人，点击「添加机器人」创建'
)
const hintText = computed(() =>
  isFeishu.value
    ? '每个飞书机器人对应飞书的一个自建应用。请在飞书开发者后台开启「机器人」能力并在「事件订阅」中填该机器人的回调 URL（编辑弹窗内显示），订阅 im.message.receive_v1，并按需填写校验 Token 与 EncryptKey。'
    : isDingtalk.value
      ? '每个钉钉机器人对应钉钉的一个企业内部应用。请在该应用后台开启「消息接收」HTTP 回调，回调地址填该机器人的回调 URL（编辑弹窗内显示），并填写 Token 与 EncodingAESKey。'
      : '每个机器人对应企微的一个自建应用。请在企微后台为该应用开通「API 接收消息」，回调地址填该机器人的回调 URL（编辑弹窗内显示），并填写 Token 与 EncodingAESKey。创建/编辑后可在弹窗底部看到回调地址。'
)

const botIsDingtalk = computed(() => (editingBot.value?.provider || 'wecom') === 'dingtalk')
const botIsFeishu = computed(() => (editingBot.value?.provider || 'wecom') === 'feishu')

const botModelOptions = computed(() => {
  if (!editingBot.value || !editingBot.value.endpoint_id) return []
  const ep = endpoints.value.find((e) => e.id === editingBot.value.endpoint_id)
  if (!ep) return []
  return String(ep.models || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
})

function botIdValue(b) {
  return isFeishu.value ? b.corp_id : b.agent_id
}

async function loadBots() {
  try {
    bots.value = await api.adminGetWecomBots(props.provider)
    botMsg.value = ''
  } catch {
    botMsg.value = '加载机器人失败'
  }
}

async function loadBotOptions() {
  try {
    endpoints.value = await api.adminEndpoints()
  } catch {}
  try {
    kbs.value = await api.adminGetKnowledgeBases()
  } catch {}
  try {
    mcps.value = await api.adminMcpServers()
  } catch {}
  try {
    skills.value = await api.adminSkills()
  } catch {}
}

function openBotCreate() {
  editingBot.value = {
    provider: props.provider,
    name: '',
    corp_id: '',
    secret: '',
    agent_id: '',
    token: '',
    aes_key: '',
    kb_ids: [],
    mcp_ids: [],
    skill_ids: [],
    web_search: 0,
    endpoint_id: null,
    model: '',
    enabled: 1,
  }
  loadBotOptions()
}

function openBotEdit(b) {
  editingBot.value = {
    id: b.id,
    provider: b.provider || props.provider,
    name: b.name,
    corp_id: b.corp_id,
    secret: '',
    agent_id: b.agent_id,
    token: '',
    aes_key: '',
    token_masked: b.token_masked,
    aes_key_set: b.aes_key_set,
    callback_url: b.callback_url,
    kb_ids: (b.kb_ids || '').split(',').filter(Boolean).map(Number),
    mcp_ids: (b.mcp_ids || '').split(',').filter(Boolean).map(Number),
    skill_ids: (b.skill_ids || '').split(',').filter(Boolean).map(Number),
    web_search: b.web_search,
    endpoint_id: b.endpoint_id,
    model: b.model,
    enabled: b.enabled,
  }
  loadBotOptions()
}

function toggleBotKb(kbId) {
  const arr = editingBot.value.kb_ids
  const idx = arr.indexOf(kbId)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(kbId)
}

function toggleBotMcp(mcpId) {
  const arr = editingBot.value.mcp_ids
  const idx = arr.indexOf(mcpId)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(mcpId)
}

function toggleBotSkill(skillId) {
  const arr = editingBot.value.skill_ids
  const idx = arr.indexOf(skillId)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(skillId)
}

async function saveBot() {
  if (!editingBot.value) return
  const f = editingBot.value
  if (!f.name) return (botMsg.value = '请填写机器人名称')
  savingBot.value = true
  botMsg.value = ''
  try {
    const body = {
      name: f.name,
      provider: f.provider || props.provider,
      corp_id: f.corp_id,
      agent_id: f.agent_id,
      token: f.token,
      kb_ids: (f.kb_ids || []).join(','),
      mcp_ids: (f.mcp_ids || []).join(','),
      skill_ids: (f.skill_ids || []).join(','),
      web_search: f.web_search || 0,
      endpoint_id: f.endpoint_id || null,
      model: f.model,
      enabled: f.enabled,
    }
    if (f.secret) body.secret = f.secret
    if (f.aes_key) body.aes_key = f.aes_key
    if (f.id) {
      await api.adminUpdateWecomBot(f.id, body)
    } else {
      await api.adminCreateWecomBot(body)
    }
    editingBot.value = null
    await loadBots()
  } catch (e) {
    botMsg.value = e.message
  } finally {
    savingBot.value = false
  }
}

async function delBot(b) {
  if (!(await confirmDlg.askConfirm(`删除机器人「${b.name}」？`, { title: '删除机器人', danger: true }))) return
  try {
    await api.adminDeleteWecomBot(b.id)
    await loadBots()
  } catch (e) {
    botMsg.value = e.message
  }
}

onMounted(loadBots)
</script>

<template>
  <div>
    <h3 class="section-title">机器人</h3>
    <div class="head">
      <span></span>
      <button class="btn" @click="openBotCreate">＋ 添加机器人</button>
    </div>
    <p v-if="botMsg" class="msg">{{ botMsg }}</p>
    <table class="table">
      <thead>
        <tr>
          <th>名称</th>
          <th>{{ idLabel }}</th>
          <th>联网</th>
          <th>知识库</th>
          <th>MCP</th>
          <th>启用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="b in bots" :key="b.id">
          <td>{{ b.name }}</td>
          <td class="mono">{{ botIdValue(b) }}</td>
          <td>{{ b.web_search ? '✓' : '✕' }}</td>
          <td>{{ b.kb_ids || '—' }}</td>
          <td>{{ b.mcp_ids || '—' }}</td>
          <td>{{ b.enabled ? '✓' : '✕' }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openBotEdit(b)">编辑</button>
            <button class="btn btn-del" @click="delBot(b)">删除</button>
          </td>
        </tr>
        <tr v-if="!bots.length">
          <td colspan="7" class="empty">{{ emptyText }}</td>
        </tr>
      </tbody>
    </table>
    <p class="hint" style="margin-top: 10px">{{ hintText }}</p>

    <div v-if="editingBot" class="modal-mask">
      <div class="modal">
        <h3>{{ editingBot.id ? '编辑机器人' : '添加机器人' }}</h3>
        <label>名称<input v-model="editingBot.name" class="input" placeholder="如 客服机器人" /></label>
        <div class="form-2">
          <label>{{ botIsDingtalk ? 'AppKey' : botIsFeishu ? 'AppID' : 'CorpID' }}<input v-model="editingBot.corp_id" class="input" :placeholder="botIsDingtalk ? '钉钉应用 AppKey' : botIsFeishu ? '飞书应用 AppID' : '留空使用企微设置中的 CorpID'" /></label>
          <label>{{ botIsDingtalk ? 'AppSecret' : botIsFeishu ? 'AppSecret' : '应用 Secret' }}<input v-model="editingBot.secret" type="password" class="input" :placeholder="editingBot.id ? '留空不修改' : (botIsDingtalk ? '钉钉应用 AppSecret' : botIsFeishu ? '飞书应用 AppSecret' : '应用 Secret')" /></label>
          <label v-if="!botIsFeishu">AgentId<input v-model="editingBot.agent_id" class="input" :placeholder="botIsDingtalk ? '钉钉应用 AgentId' : '应用 AgentId'" /></label>
          <label>{{ botIsDingtalk || botIsFeishu ? 'URL 验证 Token' : 'Token' }}<input v-model="editingBot.token" type="password" class="input" :placeholder="editingBot.id ? (editingBot.token_masked || '已设置（留空不修改）') : (botIsFeishu ? '校验 Token（选填）' : '回调 Token')" /></label>
          <label>{{ botIsFeishu ? 'EncryptKey' : botIsDingtalk ? 'EncodingAESKey' : 'EncodingAESKey' }}<input v-model="editingBot.aes_key" type="password" class="input" :placeholder="editingBot.id ? '已设置（留空不修改）' : (botIsFeishu ? 'Encrypt Key（选填）' : 'EncodingAESKey')" /></label>
        </div>
        <label>接口
          <select v-model="editingBot.endpoint_id" class="input">
            <option :value="null">默认接口</option>
            <option v-for="e in endpoints" :key="e.id" :value="e.id">{{ e.name }}</option>
          </select>
        </label>
        <label>模型
          <select v-model="editingBot.model" class="input">
            <option value="">自动（接口默认）</option>
            <option v-for="m in botModelOptions" :key="m" :value="m">{{ m }}</option>
          </select>
        </label>
        <div class="form-2">
          <label>知识库
            <div class="kb-checkbox-list">
              <label v-for="kb in kbs" :key="kb.id" class="check">
                <input type="checkbox" :value="kb.id" :checked="editingBot.kb_ids.includes(kb.id)" @change="toggleBotKb(kb.id)" />
                {{ kb.name }}
              </label>
              <span v-if="!kbs.length" class="hint">暂无知识库</span>
            </div>
          </label>
          <label class="check" style="margin-top: 10px"><input type="checkbox" v-model="editingBot.web_search" :true-value="1" :false-value="0" /> 启用联网搜索</label>
        </div>
        <label>MCP 工具（大模型选用）
          <div class="kb-checkbox-list">
            <label v-for="m in mcps" :key="m.id" class="check">
              <input type="checkbox" :value="m.id" :checked="editingBot.mcp_ids.includes(m.id)" @change="toggleBotMcp(m.id)" />
              {{ m.name }}
            </label>
            <span v-if="!mcps.length" class="hint">暂无 MCP 服务</span>
          </div>
        </label>
        <label>技能包（大模型选用）
          <div class="kb-checkbox-list">
            <label v-for="sk in skills" :key="sk.id" class="check">
              <input type="checkbox" :value="sk.id" :checked="editingBot.skill_ids.includes(sk.id)" @change="toggleBotSkill(sk.id)" />
              {{ sk.name }}
            </label>
            <span v-if="!skills.length" class="hint">暂无技能包</span>
          </div>
        </label>
        <label class="check"><input type="checkbox" v-model="editingBot.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <p v-if="editingBot.id" class="hint" style="margin-top: 8px">
          回调地址：<code>{{ editingBot.callback_url }}</code>
        </p>
        <p v-if="!editingBot.id" class="hint" style="margin-top: 8px">保存后可在此查看回调地址，填入{{ botIsDingtalk ? '钉钉' : botIsFeishu ? '飞书' : '企微' }}后台。</p>
        <div class="foot">
          <button class="btn btn-outline" @click="editingBot = null">取消</button>
          <button class="btn" :disabled="savingBot" @click="saveBot">{{ savingBot ? '保存中…' : '保存' }}</button>
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
  </div>
</template>
