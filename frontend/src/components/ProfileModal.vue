<script setup>
import { ref, computed } from 'vue'
import { api } from '../api'
import { store } from '../store'

const props = defineProps({
  user: { type: Object, required: true },
  smsEnabled: Boolean,
})
const emit = defineEmits(['close'])

const nickname = ref(props.user.nickname || '')
const currentAvatar = ref(props.user.avatar || '')
const assistantName = ref(props.user.assistant_name || '')
const currentAssistantAvatar = ref(props.user.assistant_avatar || '')

const phone = ref(props.user.phone || '')
const newPhone = ref('')
const code = ref('')
const debugCode = ref('')

const savingNick = ref(false)
const savingAssistantName = ref(false)
const uploadingAvatar = ref(false)
const uploadingAssistantAvatar = ref(false)
const sendingCode = ref(false)
const binding = ref(false)
const msg = ref('')
const msgType = ref('')

const avatarSrc = computed(() => {
  if (!currentAvatar.value) return ''
  return `/api/auth/avatar/${props.user.id}?v=${encodeURIComponent(currentAvatar.value)}`
})

const assistantAvatarSrc = computed(() => {
  if (!currentAssistantAvatar.value) return ''
  return `/api/auth/assistant-avatar/${props.user.id}?v=${encodeURIComponent(currentAssistantAvatar.value)}`
})

function setMsg(text, type = 'err') {
  msg.value = text
  msgType.value = type
}

async function saveNickname() {
  const n = nickname.value.trim()
  if (!n) return setMsg('昵称不能为空')
  savingNick.value = true
  msg.value = ''
  try {
    const r = await api.updateProfile({ nickname: n })
    store.setUser(r)
    nickname.value = r.nickname || ''
    setMsg('昵称已更新', 'ok')
  } catch (e) {
    setMsg(e.message)
  } finally {
    savingNick.value = false
  }
}

async function saveAssistantName() {
  const n = assistantName.value.trim()
  savingAssistantName.value = true
  msg.value = ''
  try {
    const r = await api.updateProfile({ assistant_name: n })
    store.setUser(r)
    assistantName.value = r.assistant_name || ''
    setMsg('助手昵称已更新', 'ok')
  } catch (e) {
    setMsg(e.message)
  } finally {
    savingAssistantName.value = false
  }
}

async function onPickAvatar(e) {
  const f = e.target.files[0]
  if (!f) return
  uploadingAvatar.value = true
  msg.value = ''
  try {
    const r = await api.uploadAvatar(f)
    store.setUser(r)
    currentAvatar.value = r.avatar || ''
    setMsg('头像已更新', 'ok')
  } catch (e) {
    setMsg(e.message)
  } finally {
    uploadingAvatar.value = false
    e.target.value = ''
  }
}

async function onPickAssistantAvatar(e) {
  const f = e.target.files[0]
  if (!f) return
  uploadingAssistantAvatar.value = true
  msg.value = ''
  try {
    const r = await api.uploadAssistantAvatar(f)
    store.setUser(r)
    currentAssistantAvatar.value = r.assistant_avatar || ''
    setMsg('助手头像已更新', 'ok')
  } catch (e) {
    setMsg(e.message)
  } finally {
    uploadingAssistantAvatar.value = false
    e.target.value = ''
  }
}

async function sendCode() {
  const p = newPhone.value.trim()
  if (!p) return setMsg('请输入新手机号')
  sendingCode.value = true
  msg.value = ''
  try {
    const r = await api.smsSend(p)
    debugCode.value = r.debug_code || ''
    setMsg(r.debug_code ? `验证码已发送（模拟：${r.debug_code}）` : '验证码已发送', 'ok')
  } catch (e) {
    setMsg(e.message)
  } finally {
    sendingCode.value = false
  }
}

async function bindPhone() {
  const p = newPhone.value.trim()
  const c = code.value.trim()
  if (!p || !c) return setMsg('请输入手机号和验证码')
  binding.value = true
  msg.value = ''
  try {
    const r = await api.updatePhone(p, c)
    store.setUser(r)
    phone.value = r.phone || ''
    newPhone.value = ''
    code.value = ''
    debugCode.value = ''
    setMsg('手机号已更新', 'ok')
  } catch (e) {
    setMsg(e.message)
  } finally {
    binding.value = false
  }
}
</script>

<template>
  <div class="modal-mask" @click.self="emit('close')">
    <div class="modal modal-profile">
      <div class="picker-head">
        <span>个人资料</span>
        <button class="picker-close" @click="emit('close')">
          <font-awesome-icon icon="xmark" />
        </button>
      </div>

      <div class="profile-body">
        <div class="avatar-row">
          <div class="avatar-preview">
            <img v-if="avatarSrc" :src="avatarSrc" alt="头像" />
            <span v-else>{{ (props.user.nickname || 'U').slice(0, 1) }}</span>
          </div>
          <label class="btn btn-outline file-btn">
            {{ uploadingAvatar ? '上传中…' : '更换头像' }}
            <input type="file" accept="image/*" :disabled="uploadingAvatar" @change="onPickAvatar" />
          </label>
        </div>

        <div class="field">
          <label>昵称</label>
          <div class="row">
            <input v-model="nickname" class="input" placeholder="请输入昵称" @keyup.enter="saveNickname" />
            <button class="btn" :disabled="savingNick" @click="saveNickname">{{ savingNick ? '保存中…' : '保存' }}</button>
          </div>
        </div>

        <div class="assistant-block">
          <h4 class="block-title">助手形象</h4>
          <div class="avatar-row">
            <div class="avatar-preview assistant-hint">
              <img v-if="assistantAvatarSrc" :src="assistantAvatarSrc" alt="助手头像" />
              <span v-else>{{ (assistantName || 'A').slice(0, 1) }}</span>
            </div>
            <label class="btn btn-outline file-btn">
              {{ uploadingAssistantAvatar ? '上传中…' : '更换助手头像' }}
              <input type="file" accept="image/*" :disabled="uploadingAssistantAvatar" @change="onPickAssistantAvatar" />
            </label>
          </div>
          <div class="field">
            <label>助手昵称 <span class="muted">（留空则使用默认）</span></label>
            <div class="row">
              <input v-model="assistantName" class="input" placeholder="默认 askaibot" @keyup.enter="saveAssistantName" />
              <button class="btn" :disabled="savingAssistantName" @click="saveAssistantName">
                {{ savingAssistantName ? '保存中…' : '保存' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="smsEnabled" class="field">
          <label>手机号 <span class="muted">（修改需短信验证）</span></label>
          <p class="curr-phone">当前：{{ phone || '未绑定' }}</p>
          <div class="row">
            <input v-model="newPhone" class="input" placeholder="新手机号" />
            <button class="btn btn-outline" :disabled="sendingCode" @click="sendCode">
              {{ sendingCode ? '发送中…' : '发送验证码' }}
            </button>
          </div>
          <div class="row">
            <input v-model="code" class="input" placeholder="验证码" @keyup.enter="bindPhone" />
            <button class="btn" :disabled="binding" @click="bindPhone">{{ binding ? '绑定中…' : '绑定手机号' }}</button>
          </div>
          <p v-if="debugCode" class="debug">模拟验证码：<b>{{ debugCode }}</b></p>
        </div>

        <p v-if="msg" class="profile-msg" :class="msgType">{{ msg }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-profile {
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
  font-size: 16px;
}

.picker-close:hover {
  color: var(--text);
  background: var(--primary-soft);
}

.profile-body {
  padding: 6px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-preview {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--primary-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: var(--primary);
  font-weight: 600;
  flex-shrink: 0;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.assistant-block {
  border-top: 1px solid var(--border);
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.block-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.assistant-hint {
  background: var(--surface);
  border: 1px dashed var(--border);
  color: var(--text-muted);
}

.file-btn {
  position: relative;
  overflow: hidden;
}

.file-btn input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 13px;
  color: var(--text-muted);
}

.muted {
  color: var(--text-muted);
  font-weight: 400;
}

.row {
  display: flex;
  gap: 8px;
}

.row .input {
  flex: 1;
}

.row .btn {
  white-space: nowrap;
}

.curr-phone {
  font-size: 13px;
}

.debug {
  font-size: 13px;
  color: var(--primary);
}

.profile-msg {
  font-size: 13px;
  color: var(--danger);
}

.profile-msg.ok {
  color: var(--primary);
}
</style>
