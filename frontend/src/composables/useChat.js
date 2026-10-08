import { ref, reactive, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api, streamChat, uploadFile } from '../api'
import { store } from '../store'
import { useConfirm } from './useConfirm'

const conversations = ref([])
const currentConversation = ref(null)
const messages = ref([])
const input = ref('')
const streaming = ref(false)
const errorMsg = ref('')
const scrollRef = ref(null)
const sidebarOpen = ref(true)

const pendingAttachments = ref([])
const uploading = ref(false)
const fileInputRef = ref(null)

const endpoints = ref([])
const selectedEndpointId = ref(null)
const selectedModel = ref('')
const endpointPickerOpen = ref(false)

const profileOpen = ref(false)
const smsEnabled = ref(false)
const searchEnabled = ref(false)
const webSearch = ref(false)

const agreementOpen = ref(false)
const pendingAgreements = ref([])

const knowledgeBases = ref([])
const selectedKnowledgeBaseId = ref(null)
const kbPickerOpen = ref(false)

const mcpServers = ref([])
const selectedMcpIds = ref([])
const mcpPickerOpen = ref(false)

const skills = ref([])
const selectedSkillIds = ref([])
const skillPickerOpen = ref(false)

const defaultAssistantName = ref('askaibot')
const defaultAssistantAvatar = ref('')

const quota = ref(null)

let router = null
const confirmDlg = useConfirm()

const me = () => store.user

const avatarSrc = computed(() => {
  const u = me()
  if (!u?.avatar) return ''
  return `/api/auth/avatar/${u.id}?v=${encodeURIComponent(u.avatar)}`
})

const assistantName = computed(
  () => me()?.assistant_name || defaultAssistantName.value || 'askaibot'
)

const assistantAvatarSrc = computed(() => {
  const u = me()
  if (u?.assistant_avatar) {
    return `/api/auth/assistant-avatar/${u.id}?v=${encodeURIComponent(u.assistant_avatar)}`
  }
  return defaultAssistantAvatar.value
})

const currentEndpointName = computed(() => {
  const ep = endpoints.value.find((e) => e.id === selectedEndpointId.value)
  return ep?.name || ''
})

const currentSelectionText = computed(() => {
  if (currentEndpointName.value && selectedModel.value) {
    return `${currentEndpointName.value}-${selectedModel.value}`
  }
  return currentEndpointName.value || '未选择'
})

const currentKnowledgeBaseText = computed(() => {
  const kb = knowledgeBases.value.find((k) => k.id === selectedKnowledgeBaseId.value)
  if (!kb) return ''
  return kb.name + (kb.provider === 'ragflow' ? '（RAGFlow）' : kb.provider === 'dify' ? '（Dify）' : '')
})

function parseMcpIds(s) {
  return (s || '')
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
    .map(Number)
}

function toggleMcp(server) {
  const i = selectedMcpIds.value.indexOf(server.id)
  if (i === -1) selectedMcpIds.value.push(server.id)
  else selectedMcpIds.value.splice(i, 1)
  persistMcpSelection()
}

function persistMcpSelection() {
  const conv = currentConversation.value
  if (!conv) return
  conv.mcp_ids = selectedMcpIds.value.join(',')
  api.updateConversationMcp(conv.id, conv.mcp_ids).catch(() => {})
}

function clearMcpSelection() {
  selectedMcpIds.value = []
  persistMcpSelection()
}

function parseSkillIds(s) {
  return (s || '')
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
    .map(Number)
}

function toggleSkill(skill) {
  const i = selectedSkillIds.value.indexOf(skill.id)
  if (i === -1) selectedSkillIds.value.push(skill.id)
  else selectedSkillIds.value.splice(i, 1)
  persistSkillSelection()
}

function persistSkillSelection() {
  const conv = currentConversation.value
  if (!conv) return
  conv.skill_ids = selectedSkillIds.value.join(',')
  api.updateConversationSkills(conv.id, conv.skill_ids).catch(() => {})
}

function clearSkillSelection() {
  selectedSkillIds.value = []
  persistSkillSelection()
}

function openProfile() {
  profileOpen.value = true
}

function openEndpointPicker() {
  endpointPickerOpen.value = true
}

function selectKnowledgeBase(kb) {
  selectedKnowledgeBaseId.value = kb ? kb.id : null
  kbPickerOpen.value = false
}

function selectModel(ep, model) {
  selectedEndpointId.value = ep.id
  selectedModel.value = model
  endpointPickerOpen.value = false
}

function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function loadEndpoints() {
  try {
    endpoints.value = await api.endpoints()
    const def = endpoints.value.find((e) => e.is_default) || endpoints.value[0]
    if (def) {
      selectedEndpointId.value = def.id
      selectedModel.value = def.models[0] || ''
    }
  } catch {
    endpoints.value = []
  }
}

async function refreshQuota() {
  try {
    quota.value = await api.quota()
  } catch {
    quota.value = null
  }
}

async function loadConversations() {
  conversations.value = await api.conversations()
  if (!currentConversation.value && conversations.value.length) {
    await selectConversation(conversations.value[0])
  }
}

async function selectConversation(conv) {
  currentConversation.value = conv
  messages.value = await api.messages(conv.id)
  selectedMcpIds.value = parseMcpIds(conv.mcp_ids)
  selectedSkillIds.value = parseSkillIds(conv.skill_ids)
  sidebarOpen.value = false
  scrollToBottom()
}

async function newConversation() {
  currentConversation.value = null
  messages.value = []
  input.value = ''
  selectedMcpIds.value = []
  selectedSkillIds.value = []
  sidebarOpen.value = false
}

async function deleteConversation(conv, e) {
  e.stopPropagation()
  if (!(await confirmDlg.askConfirm(`删除会话「${conv.title}」？`, { title: '删除会话', danger: true }))) return
  await api.deleteConversation(conv.id)
  conversations.value = conversations.value.filter((c) => c.id !== conv.id)
  if (currentConversation.value?.id === conv.id) {
    currentConversation.value = null
    messages.value = []
  }
}

async function renameConversation(conv, e) {
  e.stopPropagation()
  const title = prompt('重命名会话', conv.title)
  if (title && title.trim()) {
    const updated = await api.renameConversation(conv.id, title.trim())
    conv.title = updated.title
  }
}

function pickFiles() {
  fileInputRef.value?.click()
}

async function onFilesSelected(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  uploading.value = true
  for (const file of files) {
    try {
      const att = await uploadFile(file)
      pendingAttachments.value.push(att)
    } catch (err) {
      errorMsg.value = err.message
    }
  }
  uploading.value = false
}

function removePending(id) {
  pendingAttachments.value = pendingAttachments.value.filter((a) => a.id !== id)
}

async function send() {
  const content = input.value.trim()
  if ((!content && !pendingAttachments.value.length) || streaming.value) return
  if (!selectedEndpointId.value) {
    errorMsg.value = '请先在下方选择接口'
    return
  }
  const attachmentIds = pendingAttachments.value.map((a) => a.id)
  const endpointId = selectedEndpointId.value
  const model = selectedModel.value
  input.value = ''
  errorMsg.value = ''

  let convId = currentConversation.value?.id
  if (!convId) {
    const conv = await api.createConversation({
      title: content.slice(0, 20),
      model: '',
      mcp_ids: selectedMcpIds.value.join(','),
      skill_ids: selectedSkillIds.value.join(','),
    })
    conversations.value.unshift(conv)
    currentConversation.value = conv
    convId = conv.id
  }

  messages.value.push({ role: 'user', content, attachments: [...pendingAttachments.value] })
  pendingAttachments.value = []
  const assistant = reactive({ role: 'assistant', content: '', streaming: true, searching: false, tooling: false })
  messages.value.push(assistant)
  streaming.value = true
  scrollToBottom()

  try {
    await streamChat({
      conversationId: convId,
      content,
      attachmentIds,
      endpointId,
      model,
      webSearch: webSearch.value,
      knowledgeBaseId: selectedKnowledgeBaseId.value,
      onDelta: (d) => {
        assistant.searching = false
        assistant.tooling = false
        assistant.content += d
        scrollToBottom()
      },
      onStatus: (s) => {
        if (s === 'searching') {
          assistant.searching = true
          scrollToBottom()
        }
        if (s === 'tool') {
          assistant.tooling = true
          scrollToBottom()
        }
      },
      onError: (err) => {
        assistant.content = `⚠️ 请求出错：${err}`
      },
      onDone: () => {},
    })
  } catch (e) {
    assistant.content = `⚠️ 连接失败：${e.message}`
  } finally {
    assistant.streaming = false
    streaming.value = false
    scrollToBottom()
    loadConversations()
    refreshQuota()
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function logout() {
  store.logout()
  router?.replace('/login')
}

async function acceptPendingAgreement() {
  try {
    await api.acceptAgreement(pendingAgreements.value.map((a) => a.id))
  } catch {
    return
  }
  pendingAgreements.value = []
  agreementOpen.value = false
}

async function init() {
  if (window.innerWidth < 800) sidebarOpen.value = false
  if (!store.user) {
    try {
      store.user = await api.me()
    } catch {
      store.logout()
      router?.replace('/login')
      return
    }
  }
  try {
    const pending = await api.agreementStatus()
    if (pending.length) {
      pendingAgreements.value = pending
      agreementOpen.value = true
    }
  } catch {}
  await loadConversations()
  await loadEndpoints()
  await refreshQuota()
  try {
    knowledgeBases.value = await api.knowledgeBases()
  } catch {
    knowledgeBases.value = []
  }
  try {
    mcpServers.value = await api.mcpServers()
  } catch {
    mcpServers.value = []
  }
  try {
    skills.value = await api.skills()
  } catch {
    skills.value = []
  }
  try {
    const s = await api.getSms()
    smsEnabled.value = !!s.enabled
  } catch {}
  try {
    const s = await api.getSearch()
    searchEnabled.value = !!s.enabled
  } catch {}
  try {
    const site = await api.site()
    defaultAssistantName.value = site.assistant_name || 'askaibot'
    defaultAssistantAvatar.value = site.assistant_avatar_url || ''
  } catch {}
}

export function useChat() {
  if (!router) router = useRouter()
  return {
    conversations,
    currentConversation,
    messages,
    input,
    streaming,
    errorMsg,
    scrollRef,
    sidebarOpen,
    pendingAttachments,
    uploading,
    fileInputRef,
    endpoints,
    selectedEndpointId,
    selectedModel,
    endpointPickerOpen,
    profileOpen,
    smsEnabled,
    searchEnabled,
    webSearch,
    agreementOpen,
    pendingAgreements,
    acceptPendingAgreement,
    quota,
    knowledgeBases,
    selectedKnowledgeBaseId,
    kbPickerOpen,
    mcpServers,
    selectedMcpIds,
    mcpPickerOpen,
    skills,
    selectedSkillIds,
    skillPickerOpen,
    me,
    avatarSrc,
    assistantName,
    assistantAvatarSrc,
    currentSelectionText,
    currentKnowledgeBaseText,
    openProfile,
    openEndpointPicker,
    selectKnowledgeBase,
    selectModel,
    toggleMcp,
    clearMcpSelection,
    toggleSkill,
    clearSkillSelection,
    pickFiles,
    onFilesSelected,
    removePending,
    send,
    onKeydown,
    logout,
    selectConversation,
    newConversation,
    deleteConversation,
    renameConversation,
    init,
    scrollToBottom,
  }
}
