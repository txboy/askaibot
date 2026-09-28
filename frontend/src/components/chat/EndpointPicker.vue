<script setup>
import { useChat } from '../../composables/useChat'

const { endpointPickerOpen, endpoints, selectedEndpointId, selectedModel, selectModel } = useChat()
</script>

<template>
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
</style>
