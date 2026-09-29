<script setup>
import { computed } from 'vue'
import Logo from '../Logo.vue'
import { useChat } from '../../composables/useChat'

const {
  sidebarOpen,
  conversations,
  currentConversation,
  selectConversation,
  renameConversation,
  deleteConversation,
  newConversation,
  me,
  avatarSrc,
  openProfile,
  logout,
  quota,
} = useChat()

const quotaLow = computed(() => {
  const q = quota.value
  if (!q || q.limit == null) return false
  return q.remaining === 0 || q.remaining <= Math.max(1, Math.floor(q.limit * 0.1))
})

const quotaPct = computed(() => {
  const q = quota.value
  if (!q || q.limit == null || q.limit <= 0) return 0
  const used = Math.max(0, q.limit - (q.remaining ?? 0))
  return Math.min(100, Math.round((used / q.limit) * 100))
})
</script>

<template>
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

    <div class="sidebar-bottom">
      <div
        v-if="quota && quota.limit != null"
        class="quota-card"
        :class="{ low: quotaLow }"
      >
        <div class="quota-head">
          <span class="quota-label">今日额度</span>
          <span class="quota-value">剩余 {{ quota.remaining }} / {{ quota.limit }}</span>
        </div>
        <div class="quota-bar">
          <div class="quota-fill" :style="{ width: quotaPct + '%' }"></div>
        </div>
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
    </div>
  </aside>
</template>

<style scoped>
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

.sidebar:not(.open) {
  display: none;
}

.sidebar-logo {
  padding: 4px 8px 8px;
}

.sidebar-logo :deep(.brand-logo) {
  width: 100%;
  max-width: 170px;
  margin: 0 auto;
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

.sidebar-bottom {
  padding-top: 6px;
}

.quota-card {
  padding: 10px 12px;
  margin: 0 4px 8px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 10px;
}

.quota-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 7px;
}

.quota-label {
  font-size: 12px;
  color: var(--text-muted);
}

.quota-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
}

.quota-card.low .quota-value {
  color: var(--danger);
}

.quota-bar {
  height: 6px;
  background: var(--border);
  border-radius: 999px;
  overflow: hidden;
}

.quota-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 999px;
  transition: width 0.3s ease;
}

.quota-card.low .quota-fill {
  background: var(--danger);
}

.user-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 6px 4px;
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

@media (max-width: 800px) {
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
}
</style>
