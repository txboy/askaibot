<script setup>
import { useChat } from '../../composables/useChat'

const { kbPickerOpen, knowledgeBases, selectedKnowledgeBaseId, selectKnowledgeBase } = useChat()
</script>

<template>
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
          <span class="picker-kb-title">
            <span>{{ kb.name }}</span>
            <span class="kb-type">{{ kb.provider === 'ragflow' ? 'RAGFlow' : kb.provider === 'dify' ? 'Dify' : '' }}</span>
          </span>
          <span v-if="kb.description" class="picker-kb-desc">{{ kb.description }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
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

.picker-kb-title {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.kb-type {
  font-size: 11px;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0 5px;
}

.picker-kb.active .kb-type {
  color: rgba(255, 255, 255, 0.85);
  border-color: rgba(255, 255, 255, 0.5);
}

.picker-kb.active .picker-kb-desc {
  color: rgba(255, 255, 255, 0.85);
}
</style>
