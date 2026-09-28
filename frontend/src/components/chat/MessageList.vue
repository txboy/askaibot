<script setup>
import AttachmentImage from '../AttachmentImage.vue'
import MarkdownContent from '../MarkdownContent.vue'
import { useChat } from '../../composables/useChat'

const { messages, scrollRef, me, avatarSrc, assistantAvatarSrc, assistantName } = useChat()
</script>

<template>
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
        <div v-if="m.role === 'assistant' && m.tooling" class="searching-hint">
          <font-awesome-icon icon="plug" /> 正在调用 MCP 工具…
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
</template>

<style scoped>
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

.searching-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 5px;
}

@media (max-width: 800px) {
  .messages {
    padding: 16px 12px;
  }
}
</style>
