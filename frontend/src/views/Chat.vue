<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api, streamChat, uploadFile } from '../api'
import { store } from '../store'
import AttachmentImage from '../components/AttachmentImage.vue'
import MarkdownContent from '../components/MarkdownContent.vue'
import Logo from '../components/Logo.vue'
import ProfileModal from '../components/ProfileModal.vue'

const router = useRouter()

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

const me = () => store.user

const profileOpen = ref(false)
const smsEnabled = ref(false)
const searchEnabled = ref(false)
const webSearch = ref(false)

const knowledgeBases = ref([])
const selectedKnowledgeBaseId = ref(null)
const kbPickerOpen = ref(false)

const avatarSrc = computed(() => {
  const u = me()
  if (!u?.avatar) return ''
  return `/api/auth/avatar/${u.id}?v=${encodeURIComponent(u.avatar)}`
})

const defaultAssistantName = ref('askai')
const defaultAssistantAvatar = ref('')

const assistantName = computed(
  () => me()?.assistant_name || defaultAssistantName.value || 'askai'
)

const assistantAvatarSrc = computed(() => {
  const u = me()
  if (u?.assistant_avatar) {
    return `/api/auth/assistant-avatar/${u.id}?v=${encodeURIComponent(u.assistant_avatar)}`
  }
  return defaultAssistantAvatar.value
})

function openProfile() {
  profileOpen.value = true
}

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

function openEndpointPicker() {
  endpointPickerOpen.value = true
}

const currentKnowledgeBaseText = computed(() => {
  const kb = knowledgeBases.value.find((k) => k.id === selectedKnowledgeBaseId.value)
  return kb?.name || ''
})

function selectKnowledgeBase(kb) {
  selectedKnowledgeBaseId.value = kb ? kb.id : null
  kbPickerOpen.value = false
}

function selectModel(ep, model) {
  selectedEndpointId.value = ep.id
  selectedModel.value = model
  endpointPickerOpen.value = false
}

onMounted(async () => {
  if (window.innerWidth < 800) sidebarOpen.value = false
  if (!store.user) {
    try {
      store.user = await api.me()
    } catch {
      store.logout()
      router.replace('/login')
      return
    }
  }
  await loadConversations()
  await loadEndpoints()
  try {
    knowledgeBases.value = await api.knowledgeBases()
  } catch {
    knowledgeBases.value = []
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
    defaultAssistantName.value = site.assistant_name || 'askai'
    defaultAssistantAvatar.value = site.assistant_avatar_url || ''
  } catch {}
})

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

function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
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
  sidebarOpen.value = false
  scrollToBottom()
}

async function newConversation() {
  currentConversation.value = null
  messages.value = []
  input.value = ''
  sidebarOpen.value = false
}

async function deleteConversation(conv, e) {
  e.stopPropagation()
  if (!confirm(`删除会话「${conv.title}」？`)) return
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
    const conv = await api.createConversation({ title: content.slice(0, 20), model: '' })
    conversations.value.unshift(conv)
    currentConversation.value = conv
    convId = conv.id
  }

  messages.value.push({ role: 'user', content, attachments: [...pendingAttachments.value] })
  pendingAttachments.value = []
  const assistant = reactive({ role: 'assistant', content: '', streaming: true, searching: false })
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
        assistant.content += d
        scrollToBottom()
      },
      onStatus: (s) => {
        if (s === 'searching') {
          assistant.searching = true
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
  router.replace('/login')
}
</script>

<template>
  <div class="chat-layout">
    <div v-if="sidebarOpen" class="backdrop" @click="sidebarOpen = false"></div>

    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-logo">
        <Logo />
      </div>
      <button class="new-chat" @click="newConversation">
        <font-awesome-icon icon="plus" /> 新建对话
      </button>

      <div class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: currentConversation?.id === conv.id }"
          @click="selectConversation(conv)"
          @dblclick="renameConversation(conv, $event)"
        >
          <span class="conv-title">{{ conv.title }}</span>
          <button class="conv-del" @click="deleteConversation(conv, $event)">
            <font-awesome-icon icon="xmark" />
          </button>
        </div>
        <p v-if="!conversations.length" class="empty">暂无会话</p>
      </div>

      <div class="user-bar">
        <button class="user-info" title="编辑资料" @click="openProfile">
          <div class="avatar">
            <img v-if="avatarSrc" :src="avatarSrc" alt="头像" />
            <span v-else>{{ (me()?.nickname || 'U').slice(0, 1) }}</span>
          </div>
          <div class="user-name">{{ me()?.nickname || '用户' }}</div>
        </button>
        <button class="icon-btn" title="退出" @click="logout">
          <font-awesome-icon icon="right-from-bracket" />
        </button>
      </div>
    </aside>

    <main class="main">
      <header class="mobile-bar">
        <button class="menu-btn" title="会话" @click="sidebarOpen = !sidebarOpen">
          <font-awesome-icon icon="bars" />
        </button>
        <span class="mobile-title">AI 助手</span>
        <button class="icon-btn logout-btn" title="退出" @click="logout">
          <font-awesome-icon icon="right-from-bracket" />
        </button>
      </header>

      <div ref="scrollRef" class="messages">
        <div v-if="!messages.length" class="welcome">
          <div class="welcome-logo">✦</div>
          <h2>你好，{{ me()?.nickname }}</h2>
          <p>开始一段新对话吧</p>
        </div>

        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          <div class="msg-avatar">
            <img v-if="m.role === 'user' && avatarSrc" :src="avatarSrc" alt="头像" />
            <span v-else-if="m.role === 'user'">{{ (me()?.nickname || 'U').slice(0, 1) }}</span>
            <img v-if="m.role === 'assistant' && assistantAvatarSrc" :src="assistantAvatarSrc" alt="助手头像" />
            <span v-else-if="m.role === 'assistant'">{{ assistantName.slice(0, 1) }}</span>
          </div>
          <div class="msg-body">
            <div class="msg-label">{{ m.role === 'user' ? me()?.nickname : assistantName }}</div>
            <div v-if="m.role === 'assistant' && m.searching" class="searching-hint">
              <font-awesome-icon icon="globe" /> 正在联网搜索…
            </div>
            <div v-if="m.role === 'assistant'" class="msg-content md-body">
              <MarkdownContent :content="m.content" />
            </div>
            <div v-else class="msg-content plain">
              <div v-if="m.attachments?.length" class="att-list">
                <template v-for="a in m.attachments" :key="a.id">
                  <AttachmentImage v-if="a.kind === 'image'" :id="a.id" />
                  <span v-else class="file-chip">📄 {{ a.filename }}</span>
                </template>
              </div>
              <div v-if="m.content">{{ m.content }}</div>
            </div>
          </div>
          <span v-if="m.streaming" class="cursor">▍</span>
        </div>
      </div>

      <div class="composer">
        <input ref="fileInputRef" type="file" multiple hidden @change="onFilesSelected" />
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        <div class="composer-row">
          <div v-if="endpoints.length" class="endpoint-pick" @click="openEndpointPicker">
            <span class="endpoint-pick-label">模型</span>
            <span class="endpoint-pick-value">{{ currentSelectionText }}</span>
            <font-awesome-icon icon="chevron-down" class="endpoint-pick-caret" />
          </div>
          <p v-else class="error">暂无可用接口，请联系管理员配置</p>
          <button
            v-if="searchEnabled"
            class="web-search-toggle"
            :class="{ active: webSearch }"
            title="联网搜索"
            @click="webSearch = !webSearch"
          >
            <font-awesome-icon icon="globe" />
            <span>联网</span>
          </button>
          <button
            v-if="knowledgeBases.length"
            class="web-search-toggle kb-toggle"
            :class="{ active: selectedKnowledgeBaseId }"
            title="选择知识库"
            @click="kbPickerOpen = true"
          >
            <font-awesome-icon icon="database" />
            <span>{{ currentKnowledgeBaseText || '知识库' }}</span>
            <font-awesome-icon
              v-if="selectedKnowledgeBaseId"
              icon="xmark"
              class="kb-clear"
              @click.stop="selectKnowledgeBase(null)"
            />
          </button>
        </div>
        <div v-if="pendingAttachments.length" class="pending">
          <div v-for="a in pendingAttachments" :key="a.id" class="pending-item">
            <span class="file-chip">📄 {{ a.filename }}</span>
            <button class="pending-del" @click="removePending(a.id)">
              <font-awesome-icon icon="xmark" />
            </button>
          </div>
        </div>
        <div class="composer-box">
          <button class="attach-btn" :disabled="uploading" title="上传文件" @click="pickFiles">
            <font-awesome-icon v-if="!uploading" icon="paperclip" />
            <span v-else>…</span>
          </button>
          <textarea
            v-model="input"
            class="input"
            rows="2"
            placeholder="输入消息，按 Enter 发送，Shift+Enter 换行"
            @keydown="onKeydown"
          ></textarea>
          <button class="btn send-btn" :disabled="streaming || (!input.trim() && !pendingAttachments.length)" @click="send">发送</button>
        </div>
      </div>
    </main>

    <div v-if="endpointPickerOpen" class="modal-mask" @click.self="endpointPickerOpen = false">
      <div class="modal modal-picker">
        <div class="picker-head">
          <span>选择接口与模型</span>
          <button class="picker-close" @click="endpointPickerOpen = false">
            <font-awesome-icon icon="xmark" />
          </button>
        </div>
        <div class="picker-list">
          <div v-for="ep in endpoints" :key="ep.id" class="picker-group">
            <div class="picker-endpoint">
              <span>{{ ep.name }}{{ ep.is_default ? '（默认）' : '' }}</span>
              <span class="picker-count">{{ ep.models?.length || 0 }} 个模型</span>
            </div>
            <div class="picker-models">
              <button
                v-for="m in ep.models"
                :key="m"
                class="picker-model"
                :class="{ active: selectedEndpointId === ep.id && selectedModel === m }"
                @click="selectModel(ep, m)"
              >
                {{ m }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="kbPickerOpen" class="modal-mask" @click.self="kbPickerOpen = false">
      <div class="modal modal-picker">
        <div class="picker-head">
          <span>选择知识库</span>
          <button class="picker-close" @click="kbPickerOpen = false">
            <font-awesome-icon icon="xmark" />
          </button>
        </div>
        <div class="picker-list">
          <button
            class="picker-kb"
            :class="{ active: selectedKnowledgeBaseId === null }"
            @click="selectKnowledgeBase(null)"
          >
            <span>不使用知识库</span>
          </button>
          <button
            v-for="kb in knowledgeBases"
            :key="kb.id"
            class="picker-kb"
            :class="{ active: selectedKnowledgeBaseId === kb.id }"
            @click="selectKnowledgeBase(kb)"
          >
            <span>{{ kb.name }}</span>
            <span v-if="kb.description" class="picker-kb-desc">{{ kb.description }}</span>
          </button>
        </div>
      </div>
    </div>

    <ProfileModal
      v-if="profileOpen && me()"
      :user="me()"
      :sms-enabled="smsEnabled"
      @close="profileOpen = false"
    />
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 14px;
  gap: 14px;
}

.mobile-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
}

.menu-btn {
  font-size: 20px;
  color: var(--text);
  padding: 4px 8px;
  border-radius: 6px;
}

.menu-btn:hover {
  background: var(--primary-soft);
}

.mobile-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.logout-btn {
  margin-left: auto;
}

.sidebar:not(.open) {
  display: none;
}

.backdrop {
  display: none;
}

.new-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 11px;
  border-radius: 10px;
  background: var(--primary);
  color: #fff;
  font-weight: 500;
  transition: background 0.15s;
}

.sidebar-logo {
  padding: 4px 8px 8px;
}

.sidebar-logo :deep(.brand-logo) {
  width: 100%;
  max-width: 170px;
  margin: 0 auto;
}

.new-chat:hover {
  background: var(--primary-hover);
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
}

.conv-item:hover {
  background: var(--surface-soft);
  color: var(--text);
}

.conv-item.active {
  background: var(--primary-soft);
  color: var(--text);
}

.conv-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
}

.conv-del {
  opacity: 0;
  color: var(--text-muted);
}

.conv-item:hover .conv-del {
  opacity: 1;
}

.conv-del:hover {
  color: var(--danger);
}

.empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  margin-top: 24px;
}

.user-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-top: 1px solid var(--border);
}

.user-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 4px;
  border-radius: 8px;
  color: var(--text);
  text-align: left;
}

.user-info:hover {
  background: var(--primary-soft);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary-soft);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-name {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.icon-btn {
  color: var(--text-muted);
  font-size: 16px;
  padding: 4px;
  border-radius: 6px;
}

.icon-btn:hover {
  color: var(--text);
  background: var(--primary-soft);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.welcome {
  margin: auto;
  text-align: center;
  color: var(--text-muted);
}

.welcome-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 12px;
  border-radius: 16px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome h2 {
  color: var(--text);
  margin-bottom: 6px;
}

.msg {
  display: flex;
  gap: 10px;
  width: 100%;
  align-items: flex-start;
}

.msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
  text-align: right;
}

.msg.assistant {
  align-self: flex-start;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  overflow: hidden;
  flex-shrink: 0;
  font-size: 13px;
}

.msg-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.msg-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  max-width: calc(100% - 42px);
}

.msg.user .msg-body {
  align-items: flex-end;
}

.msg.assistant .msg-body {
  align-items: flex-start;
}

.msg-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.msg-content {
  display: inline-block;
  text-align: left;
  max-width: 100%;
}

.msg.user .msg-content.plain {
  background: var(--primary-soft);
  padding: 10px 14px;
  border-radius: 14px 14px 4px 14px;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}

.msg.assistant .msg-content.md-body {
  display: block;
}

.att-list {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  margin-bottom: 4px;
}

.file-chip {
  display: inline-block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 13px;
  color: var(--text);
}

.cursor {
  color: var(--primary);
  animation: blink 1s step-start infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.composer {
  border-top: 1px solid var(--border);
  padding: 12px 40px 20px;
}

.composer-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.composer-row .endpoint-pick {
  margin-bottom: 0;
  flex: 1;
}

.endpoint-pick {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  cursor: pointer;
  min-width: 0;
}

.endpoint-pick:hover {
  border-color: var(--primary);
}

.web-search-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 13px;
  flex-shrink: 0;
}

.web-search-toggle:hover {
  border-color: var(--primary);
  color: var(--text);
}

.web-search-toggle.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.kb-toggle .kb-clear {
  margin-left: 2px;
  font-size: 11px;
}

.kb-toggle .kb-clear:hover {
  color: var(--danger);
}

.picker-kb {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  text-align: left;
  margin-bottom: 8px;
}

.picker-kb:hover {
  border-color: var(--primary);
}

.picker-kb.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.picker-kb-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.picker-kb.active .picker-kb-desc {
  color: rgba(255, 255, 255, 0.85);
}

.searching-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.endpoint-pick-label {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.endpoint-pick-value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.endpoint-pick-caret {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 12px;
}

.pending {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px 6px 4px 10px;
}

.pending-del {
  color: var(--text-muted);
}

.pending-del:hover {
  color: var(--danger);
}

.composer-box {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 8px;
}

.attach-btn {
  font-size: 20px;
  padding: 4px 8px;
  color: var(--text-muted);
}

.attach-btn:hover {
  color: var(--primary);
}

.composer .input {
  border: none;
  resize: none;
  background: transparent;
  flex: 1;
  max-height: 200px;
}

.send-btn {
  flex-shrink: 0;
}

.error {
  font-size: 13px;
  color: var(--danger);
  margin-bottom: 6px;
}

.modal-picker {
  display: flex;
  flex-direction: column;
  max-height: 80vh;
  padding: 0;
  overflow: hidden;
}

.picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
}

.picker-close {
  color: var(--text-muted);
  padding: 4px;
  border-radius: 6px;
}

.picker-close:hover {
  color: var(--text);
  background: var(--primary-soft);
}

.picker-list {
  overflow-y: auto;
  padding: 10px 18px 18px;
}

.picker-group + .picker-group {
  margin-top: 14px;
}

.picker-endpoint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.picker-count {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}

.picker-models {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.picker-model {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  max-width: 100%;
  word-break: break-word;
}

.picker-model:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.picker-model.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

@media (max-width: 800px) {
  .backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 40;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 50;
    transform: translateX(-100%);
    transition: transform 0.22s ease;
    box-shadow: var(--shadow);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .messages {
    padding: 16px 12px;
  }

  .composer {
    padding: 10px 12px 14px;
  }

  .endpoint-pick {
    margin-bottom: 8px;
  }

  .composer-box {
    padding: 8px;
  }
}
</style>
