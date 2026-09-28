<script setup>
import { onMounted } from 'vue'
import ChatSidebar from '../components/chat/ChatSidebar.vue'
import MessageList from '../components/chat/MessageList.vue'
import ChatComposer from '../components/chat/ChatComposer.vue'
import EndpointPicker from '../components/chat/EndpointPicker.vue'
import KnowledgeBasePicker from '../components/chat/KnowledgeBasePicker.vue'
import McpPicker from '../components/chat/McpPicker.vue'
import SkillPicker from '../components/chat/SkillPicker.vue'
import ProfileModal from '../components/ProfileModal.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { useChat } from '../composables/useChat'
import { useConfirm } from '../composables/useConfirm'

const { sidebarOpen, me, profileOpen, smsEnabled, logout, init } = useChat()
const confirmDlg = useConfirm()

onMounted(init)
</script>

<template>
  <div class="chat-layout">
    <div v-if="sidebarOpen" class="backdrop" @click="sidebarOpen = false"></div>

    <ChatSidebar />

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

      <MessageList />
      <ChatComposer />
    </main>

    <EndpointPicker />
    <KnowledgeBasePicker />
    <McpPicker />
    <SkillPicker />

    <ProfileModal
      v-if="profileOpen && me()"
      :user="me()"
      :sms-enabled="smsEnabled"
      @close="profileOpen = false"
    />

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

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
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

.backdrop {
  display: none;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

@media (max-width: 800px) {
  .backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 40;
  }
}
</style>
