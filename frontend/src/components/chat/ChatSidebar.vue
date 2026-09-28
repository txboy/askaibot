<script setup>
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
} = useChat()
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
