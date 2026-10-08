<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '' },
  danger: { type: Boolean, default: false },
})
defineEmits(['confirm', 'cancel'])
</script>

<template>
  <div v-if="visible" class="confirm-mask" @click.self="$emit('cancel')">
    <div class="confirm-dialog">
      <h3 class="confirm-title">{{ title }}</h3>
      <p class="confirm-msg">{{ message }}</p>
      <div class="confirm-actions">
        <button class="btn btn-outline" @click="$emit('cancel')">取消</button>
        <button class="btn" :class="{ 'btn-danger': danger }" @click="$emit('confirm')">确认</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.confirm-dialog {
  width: 320px;
  max-width: calc(100vw - 40px);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
}

.confirm-title {
  font-size: 16px;
  margin-bottom: 10px;
}

.confirm-msg {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 18px;
  word-break: break-word;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-danger {
  background: var(--danger);
}

.btn-danger:hover {
  background: #c94440;
}
</style>
