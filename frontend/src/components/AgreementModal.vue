<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  agreements: { type: Array, default: () => [] },
  title: { type: String, default: '协议' },
  confirmable: { type: Boolean, default: true },
  canCancel: { type: Boolean, default: true },
})
const emit = defineEmits(['confirm', 'cancel'])

const checked = ref(false)

watch(
  () => props.visible,
  (v) => {
    if (!v) checked.value = false
  }
)

function cancel() {
  if (props.canCancel) emit('cancel')
}

function confirm() {
  emit('confirm', props.agreements.map((a) => a.id))
}
</script>

<template>
  <div v-if="visible" class="agree-mask" @click.self="cancel">
    <div class="agree-dialog">
      <h3 class="agree-title">{{ title }}</h3>
      <div class="agree-body">
        <div v-for="a in agreements" :key="a.id" class="agree-item">
          <h4 class="agree-item-title">{{ a.title }}</h4>
          <pre class="agree-content">{{ a.content || '（暂无内容）' }}</pre>
        </div>
        <p v-if="!agreements.length" class="agree-empty">暂无协议内容</p>
      </div>
      <div class="agree-foot">
        <label v-if="confirmable" class="agree-check">
          <input type="checkbox" v-model="checked" />
          我已阅读并同意
        </label>
        <div class="agree-actions">
          <button v-if="canCancel" class="btn btn-outline" @click="cancel">
            {{ confirmable ? '取消' : '关闭' }}
          </button>
          <button v-if="!confirmable && !canCancel" class="btn btn-outline" @click="cancel">关闭</button>
          <button v-if="confirmable" class="btn" :disabled="!checked" @click="confirm">
            确认
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agree-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
}

.agree-dialog {
  width: 560px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 60px);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
}

.agree-title {
  font-size: 16px;
  margin-bottom: 14px;
}

.agree-body {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  background: var(--surface-soft);
  max-height: 45vh;
}

.agree-item + .agree-item {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.agree-item-title {
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--text);
}

.agree-content {
  font-size: 13px;
  color: var(--text-muted);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.7;
}

.agree-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 20px 0;
}

.agree-foot {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.agree-check {
  font-size: 13px;
  color: var(--text);
}

.agree-check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
}

.agree-check input {
  cursor: pointer;
}

.agree-actions {
  display: flex;
  gap: 10px;
}
</style>
