<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const kbs = ref([])
const kbMsg = ref('')
const savingKb = ref(false)
const testingKb = ref(false)
const kbTestResult = ref('')
const editingKb = ref(null)
const confirmDlg = useConfirm()

async function loadKbs() {
  try {
    kbs.value = await api.adminGetKnowledgeBases()
    kbMsg.value = ''
  } catch (e) {
    kbMsg.value = '加载知识库失败'
  }
}

function openKbCreate() {
  editingKb.value = { name: '', provider: 'dify', base_url: '', api_key: '', dataset_ids: '', top_k: 5, mode: 'frontend', description: '', enabled: 1 }
  kbTestResult.value = ''
}

function openKbEdit(kb) {
  editingKb.value = {
    id: kb.id,
    name: kb.name,
    provider: kb.provider || 'dify',
    base_url: kb.base_url,
    api_key: '',
    dataset_ids: kb.dataset_ids || '',
    top_k: kb.top_k || 5,
    mode: kb.mode || 'frontend',
    description: kb.description,
    enabled: kb.enabled,
  }
  kbTestResult.value = ''
}

async function saveKb() {
  if (!editingKb.value) return
  const f = editingKb.value
  if (!f.name || !f.base_url) return (kbMsg.value = '请填写名称和地址')
  savingKb.value = true
  kbMsg.value = ''
  try {
    const body = { name: f.name, provider: f.provider, base_url: f.base_url, dataset_ids: f.dataset_ids || '', top_k: Number(f.top_k) || 5, mode: f.mode, description: f.description || '', enabled: f.enabled }
    if (f.api_key) body.api_key = f.api_key
    if (f.id) {
      await api.adminUpdateKnowledgeBase(f.id, body)
    } else {
      await api.adminCreateKnowledgeBase(body)
    }
    editingKb.value = null
    await loadKbs()
  } catch (e) {
    kbMsg.value = e.message
  } finally {
    savingKb.value = false
  }
}

async function testKb() {
  if (!editingKb.value) return
  const f = editingKb.value
  if (!f.base_url || !f.dataset_ids) return (kbTestResult.value = '请填写地址和数据集ID')
  testingKb.value = true
  kbTestResult.value = ''
  try {
    const res = await api.adminTestKnowledgeBase({
      provider: f.provider,
      base_url: f.base_url,
      api_key: f.api_key || '',
      dataset_ids: f.dataset_ids || '',
      top_k: Number(f.top_k) || 5,
      query: '测试',
    })
    const hits = res.results || []
    if (hits.length) {
      kbTestResult.value = `检索成功，命中 ${hits.length} 条：\n` + hits.map((h) => `- ${h.title || '片段'}`).join('\n')
    } else {
      kbTestResult.value = '检索成功，但未命中结果。'
    }
  } catch (e) {
    kbTestResult.value = '检索失败：' + (e.message || e)
  } finally {
    testingKb.value = false
  }
}

async function delKb(kb) {
  if (!(await confirmDlg.askConfirm(`删除知识库「${kb.name}」？`, { title: '删除知识库', danger: true }))) return
  try {
    await api.adminDeleteKnowledgeBase(kb.id)
    await loadKbs()
  } catch (e) {
    kbMsg.value = e.message
  }
}

onMounted(loadKbs)
</script>

<template>
  <section class="content">
    <div class="head">
      <h2>知识库</h2>
      <button class="btn" @click="openKbCreate">＋ 添加知识库</button>
    </div>
    <p v-if="kbMsg" class="msg">{{ kbMsg }}</p>
    <table class="table">
      <thead>
        <tr>
          <th>名称</th>
          <th>类型</th>
          <th>模式</th>
          <th>数据集ID</th>
          <th>地址</th>
          <th>说明</th>
          <th>启用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="kb in kbs" :key="kb.id">
          <td>{{ kb.name }}</td>
          <td>{{ kb.provider === 'ragflow' ? 'RAGFlow' : 'Dify' }}</td>
          <td>{{ kb.mode === 'llm' ? 'LLM自选' : '前台选择' }}</td>
          <td class="mono">{{ kb.dataset_ids || '—' }}</td>
          <td class="mono">{{ kb.base_url }}</td>
          <td>{{ kb.description || '—' }}</td>
          <td>{{ kb.enabled ? '✓' : '✕' }}</td>
          <td class="ops">
            <button class="btn btn-edit" @click="openKbEdit(kb)">编辑</button>
            <button class="btn btn-del" @click="delKb(kb)">删除</button>
          </td>
        </tr>
        <tr v-if="!kbs.length">
          <td colspan="8" class="empty">暂无知识库，点击「添加知识库」创建</td>
        </tr>
      </tbody>
    </table>
    <p class="hint" style="margin-top: 10px">
      知识库仅对接 <strong>Dify</strong> 与 <strong>RAGFlow</strong> 的检索 API。模式：<strong>前台选择</strong>（在聊天界面由用户选用并注入上下文）/ <strong>LLM自选</strong>（作为工具由大模型自主检索，前端无感，企微机器人仅用此模式）。数据集ID支持逗号分隔（Dify 取第一个）。
    </p>

    <div v-if="editingKb" class="modal-mask">
      <div class="modal">
        <h3>{{ editingKb.id ? '编辑知识库' : '添加知识库' }}</h3>
        <label>名称<input v-model="editingKb.name" class="input" placeholder="如 内部文档" /></label>
        <div class="form-2">
          <label>类型
            <select v-model="editingKb.provider" class="input">
              <option value="dify">Dify</option>
              <option value="ragflow">RAGFlow</option>
            </select>
          </label>
          <label>使用模式
            <select v-model="editingKb.mode" class="input">
              <option value="frontend">前台选择</option>
              <option value="llm">LLM自选（默认）</option>
            </select>
          </label>
        </div>
        <label>数据集ID<input v-model="editingKb.dataset_ids" class="input" placeholder="如 482b9a…，多个用英文逗号分隔" /></label>
        <label>API 地址<input v-model="editingKb.base_url" class="input" :placeholder="editingKb.provider === 'ragflow' ? '如 http://ragflow-host:9380' : '如 https://api.dify.ai/v1'" /></label>
        <label>API Key<input v-model="editingKb.api_key" type="password" class="input" :placeholder="editingKb.id ? '留空则不修改' : 'Bearer 密钥（Dify 数据集 Key / RAGFlow API Key）'" /></label>
        <label>返回条数（top_k）<input v-model="editingKb.top_k" type="number" class="input" min="1" /></label>
        <label>说明<textarea v-model="editingKb.description" class="input" rows="2" placeholder="知识库简介（可选）"></textarea></label>
        <label class="check"><input type="checkbox" v-model="editingKb.enabled" :true-value="1" :false-value="0" /> 启用</label>
        <div class="kb-test">
          <button class="btn btn-outline" :disabled="testingKb" @click="testKb">{{ testingKb ? '测试中…' : '测试检索' }}</button>
          <span v-if="kbTestResult" class="kb-test-result">{{ kbTestResult }}</span>
        </div>
        <div class="foot">
          <button class="btn btn-outline" @click="editingKb = null">取消</button>
          <button class="btn" :disabled="savingKb" @click="saveKb">{{ savingKb ? '保存中…' : '保存' }}</button>
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
