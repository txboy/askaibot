<script setup>
import { ref, watch } from 'vue'
import { useChat } from '../../composables/useChat'

const {
  endpoints,
  errorMsg,
  currentSelectionText,
  openEndpointPicker,
  searchEnabled,
  webSearch,
  knowledgeBases,
  selectedKnowledgeBaseId,
  currentKnowledgeBaseText,
  kbPickerOpen,
  selectKnowledgeBase,
  mcpServers,
  selectedMcpIds,
  mcpPickerOpen,
  clearMcpSelection,
  skills,
  selectedSkillIds,
  skillPickerOpen,
  clearSkillSelection,
  pendingAttachments,
  uploading,
  fileInputRef,
  pickFiles,
  onFilesSelected,
  removePending,
  input,
  streaming,
  onKeydown,
  send,
} = useChat()

const messageInput = ref(null)

function autoResize() {
  const el = messageInput.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

watch(input, autoResize)
</script>

<template>
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
      <button
        v-if="mcpServers.length"
        class="web-search-toggle mcp-toggle"
        :class="{ active: selectedMcpIds.length }"
        title="选择 MCP 工具"
        @click="mcpPickerOpen = true"
      >
        <font-awesome-icon icon="plug" />
        <span>{{ selectedMcpIds.length ? `${selectedMcpIds.length} 个MCP` : 'MCP' }}</span>
        <font-awesome-icon
          v-if="selectedMcpIds.length"
          icon="xmark"
          class="kb-clear"
          @click.stop="clearMcpSelection"
        />
      </button>
      <button
        v-if="skills.length"
        class="web-search-toggle mcp-toggle"
        :class="{ active: selectedSkillIds.length }"
        title="选择技能包"
        @click="skillPickerOpen = true"
      >
        <font-awesome-icon icon="wand-magic-sparkles" />
        <span>{{ selectedSkillIds.length ? `${selectedSkillIds.length} 个技能` : '技能' }}</span>
        <font-awesome-icon
          v-if="selectedSkillIds.length"
          icon="xmark"
          class="kb-clear"
          @click.stop="clearSkillSelection"
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
        ref="messageInput"
        class="input"
        rows="1"
        placeholder="输入消息，按 Enter 发送，Shift+Enter 换行"
        @keydown="onKeydown"
        @input="autoResize"
      ></textarea>
      <button class="btn send-btn" :disabled="streaming || (!input.trim() && !pendingAttachments.length)" @click="send">发送</button>
    </div>
  </div>
</template>

<style scoped>
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
  font-size: 13px;
  line-height: 1.3;
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
  line-height: 1.3;
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
  align-self: center;
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
  line-height: 1.5;
}

.send-btn {
  flex-shrink: 0;
  line-height: 1.5;
}

.error {
  font-size: 13px;
  color: var(--danger);
  margin-bottom: 6px;
}

@media (max-width: 800px) {
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
