<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'
import UserScopeControl from '../../components/admin/UserScopeControl.vue'

const mcps = ref([])
const mcpMsg = ref('')
const savingMcp = ref(false)
const editingMcp = ref(null)
const mcpTestTools = ref(null)
const confirmDlg = useConfirm()
const mcpTransports = [
  { value: 'http', label: 'HTTP（Streamable HTTP）' },
  { value: 'stdio', label: '本地 stdio 子进程' },
]
const mcpModes = [
  { value: 'llm', label: '大模型选用（默认注入）' },
  { value: 'frontend', label: '前端选用（用户勾选）' },
]

async function loadMcps() {
  try {
    mcps.value = await api.adminMcpServers()
    mcpMsg.value = ''
  } catch {
    mcpMsg.value = '加载 MCP 服务失败'
  }
}

function openMcpCreate() {
  editingMcp.value = {
    name: '',
    description: '',
    transport: 'http',
    url: '',
    headers: '',
    command: '',
    args: '[]',
    env: '{}',
    mode: 'llm',
    enabled: 1,
    scope: 'global',
    group_ids: [],
    tools: [],
  }
}

function openMcpEdit(m) {
  editingMcp.value = {
    id: m.id,
    name: m.name,
    description: m.description || '',
    transport: m.transport,
    url: m.url || '',
    headers: '',
    command: m.command || '',
    args: m.args || '[]',
    env: m.env || '{}',
    mode: m.mode,
    enabled: m.enabled,
    scope: m.scope || 'global',
    group_ids: (m.group_ids || []).slice(),
    tools: m.tools || [],
  }
}

async function saveMcp() {
  if (!editingMcp.value) return
  const f = editingMcp.value
  if (!f.name) return (mcpMsg.value = '请填写服务名称')
  savingMcp.value = true
  mcpMsg.value = ''
  try {
    const body = {
      name: f.name,
      description: f.description || '',
      transport: f.transport,
      url: f.url || '',
      command: f.command || '',
      args: f.args || '[]',
      env: f.env || '{}',
      mode: f.mode,
      enabled: f.enabled,
      scope: f.scope,
      group_ids: f.scope === 'group' ? f.group_ids : [],
    }
    if (f.transport === 'http' && f.headers) body.headers = f.headers
    if (f.id) {
      await api.adminUpdateMcp(f.id, body)
    } else {
      body.headers = f.headers || '{}'
      await api.adminCreateMcp(body)
    }
    editingMcp.value = null
    await loadMcps()
  } catch (e) {
    mcpMsg.value = e.message
  } finally {
    savingMcp.value = false
  }
}

async function delMcp(m) {
  if (!(await confirmDlg.askConfirm(`删除 MCP 服务「${m.name}」？`, { title: '删除 MCP 服务', danger: true }))) return
  try {
    await api.adminDeleteMcp(m.id)
    await loadMcps()
  } catch (e) {
    mcpMsg.value = e.message
  }
}

async function testMcp(m) {
  try {
    const tools = await api.adminTestMcp(m.id)
    mcpTestTools.value = { name: m.name, tools, error: '' }
  } catch (e) {
    mcpTestTools.value = { name: m.name, tools: [], error: e.message }
  }
}

async function refreshMcpTools() {
  const f = editingMcp.value
  if (!f || !f.id) return
  mcpMsg.value = ''
  try {
    const tools = await api.adminRefreshMcp(f.id)
    f.tools = tools
    mcpMsg.value = `已刷新，共 ${tools.length} 个工具`
  } catch (e) {
    mcpMsg.value = e.message
  }
}

onMounted(loadMcps)
</script>

<template>
  <section class="content">
    <div class="head">
      <h2>MCP 工具</h2>
      <button class="btn" @click="openMcpCreate">＋ 添加 MCP 服务</button>
    </div>
    <p v-if="mcpMsg" class="msg">{{ mcpMsg }}</p>
    <table class="table">
      <thead>
        <tr>
          <th>名称</th>
          <th>传输</th>
          <th>模式</th>
          <th>工具数</th>
          <th>启用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in mcps" :key="m.id">
          <td>{{ m.name }}</td>
          <td>{{ m.transport === 'stdio' ? 'stdio' : 'HTTP' }}</td>
          <td>{{ m.mode === 'frontend' ? '前端选用' : '大模型选用' }}</td>
          <td>{{ m.tools?.length || 0 }}</td>
          <td>{{ m.enabled ? '✓' : '✕' }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openMcpEdit(m)">编辑</button>
            <button class="btn btn-test" @click="testMcp(m)">测试</button>
            <button class="btn btn-del" @click="delMcp(m)">删除</button>
          </td>
        </tr>
        <tr v-if="!mcps.length">
          <td colspan="6" class="empty">暂无 MCP 服务，点击「添加 MCP 服务」创建</td>
        </tr>
      </tbody>
    </table>
    <p class="hint" style="margin-top: 10px">
      MCP（Model Context Protocol）通过工具调用让大模型连接外部服务。HTTP 使用 Streamable HTTP 传输；stdio 在服务端启动本地子进程（配置 command/args/env）。「大模型选用」的工具默认注入、模型自主调用；「前端选用」的工具由用户在聊天页勾选启用。可在企微机器人中配置 MCP，让机器人自动选用。
    </p>

    <div v-if="editingMcp" class="modal-mask">
      <div class="modal">
        <h3>{{ editingMcp.id ? '编辑 MCP 服务' : '添加 MCP 服务' }}</h3>
        <label>名称<input v-model="editingMcp.name" class="input" placeholder="如 天气服务" /></label>
        <label>说明<textarea v-model="editingMcp.description" class="input" rows="2" placeholder="服务简介（可选）"></textarea></label>
        <label>传输方式
          <select v-model="editingMcp.transport" class="input">
            <option v-for="t in mcpTransports" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </label>
        <template v-if="editingMcp.transport === 'http'">
          <label>服务地址<input v-model="editingMcp.url" class="input" placeholder="如 https://mcp.example/mcp" /></label>
          <label>请求头（JSON）<textarea v-model="editingMcp.headers" class="input mono" rows="2" :placeholder="editingMcp.id ? '已设置（留空不修改）' : '如：Authorization: Bearer xxx'"></textarea></label>
        </template>
        <template v-else>
          <label>命令<input v-model="editingMcp.command" class="input" placeholder="如 npx / uvx" /></label>
          <label>参数（JSON 数组）<textarea v-model="editingMcp.args" class="input mono" rows="2" placeholder='如 ["-y","@modelcontextprotocol/server-xxx"]'></textarea></label>
          <label>环境变量（JSON）<textarea v-model="editingMcp.env" class="input mono" rows="2" placeholder='如 {"API_KEY":"xxx"}'></textarea></label>
        </template>
        <label>选用模式
          <select v-model="editingMcp.mode" class="input">
            <option v-for="mo in mcpModes" :key="mo.value" :value="mo.value">{{ mo.label }}</option>
          </select>
        </label>
        <label class="check"><input type="checkbox" v-model="editingMcp.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <UserScopeControl v-model:scope="editingMcp.scope" v-model:groups="editingMcp.group_ids" />
        <div v-if="editingMcp.tools.length" class="mcp-tools">
          <strong>已发现工具：</strong>
          <ul class="tools-list">
            <li v-for="t in editingMcp.tools" :key="t.name">
              <code>{{ t.name }}</code><span class="hint">{{ t.description || '' }}</span>
            </li>
          </ul>
          <button v-if="editingMcp.id" class="btn btn-outline" @click="refreshMcpTools">刷新工具列表</button>
        </div>
        <div class="foot">
          <button class="btn btn-outline" @click="editingMcp = null">取消</button>
          <button class="btn" :disabled="savingMcp" @click="saveMcp">{{ savingMcp ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="mcpTestTools" class="modal-mask">
      <div class="modal">
        <h3>{{ mcpTestTools.name }} — 工具列表</h3>
        <p v-if="mcpTestTools.error" class="msg">{{ mcpTestTools.error }}</p>
        <ul v-if="mcpTestTools.tools.length" class="tools-list">
          <li v-for="t in mcpTestTools.tools" :key="t.name">
            <code>{{ t.name }}</code><span class="hint">{{ t.description || '' }}</span>
          </li>
        </ul>
        <p v-if="!mcpTestTools.tools.length && !mcpTestTools.error" class="hint">未发现工具</p>
        <div class="foot"><button class="btn" @click="mcpTestTools = null">关闭</button></div>
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
