<script setup>
import { useChat } from '../../composables/useChat'

const { skillPickerOpen, skills, selectedSkillIds, toggleSkill } = useChat()
</script>

<template>
  <div v-if="skillPickerOpen" class="modal-mask" @click.self="skillPickerOpen = false">
    <div class="modal modal-picker">
      <div class="picker-head">
        <span>选择技能包（可多选）</span>
        <button class="picker-close" @click="skillPickerOpen = false">
          <font-awesome-icon icon="xmark" />
        </button>
      </div>
      <div class="picker-list">
        <div
          v-for="sk in skills"
          :key="sk.id"
          class="picker-kb mcp-item"
          :class="{ active: selectedSkillIds.includes(sk.id) }"
          @click="toggleSkill(sk)"
        >
          <span>{{ sk.name }}</span>
          <span v-if="sk.description" class="picker-kb-desc">{{ sk.description }}</span>
          <span class="mcp-count">{{ sk.tools?.length || 0 }} 个工具</span>
        </div>
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

.mcp-item {
  align-items: center;
}

.mcp-item .mcp-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
}

.mcp-item.active .mcp-count {
  color: rgba(255, 255, 255, 0.85);
}
</style>
