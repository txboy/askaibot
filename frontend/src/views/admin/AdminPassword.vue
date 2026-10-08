<script setup>
import { ref } from 'vue'
import { api } from '../../api'

const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const pwdMsg = ref('')
const savingPwd = ref(false)

async function changePassword() {
  if (!oldPwd.value || !newPwd.value) return (pwdMsg.value = '请填写当前密码和新密码')
  if (newPwd.value !== confirmPwd.value) return (pwdMsg.value = '两次输入的新密码不一致')
  savingPwd.value = true
  pwdMsg.value = ''
  try {
    await api.adminChangePassword({ old_password: oldPwd.value, new_password: newPwd.value })
    pwdMsg.value = '密码已修改'
    oldPwd.value = newPwd.value = confirmPwd.value = ''
  } catch (e) {
    pwdMsg.value = e.message
  } finally {
    savingPwd.value = false
  }
}
</script>

<template>
  <section class="content">
    <h2>修改密码</h2>
    <div class="card card-form">
      <label>当前密码<input v-model="oldPwd" type="password" class="input" placeholder="请输入当前密码" @keyup.enter="changePassword" /></label>
      <label>新密码<input v-model="newPwd" type="password" class="input" placeholder="至少 6 位" @keyup.enter="changePassword" /></label>
      <label>确认新密码<input v-model="confirmPwd" type="password" class="input" placeholder="再次输入新密码" @keyup.enter="changePassword" /></label>
      <p v-if="pwdMsg" class="hint" :class="{ 'hint-danger': pwdMsg.includes('不正确') || pwdMsg.includes('一致') || pwdMsg.includes('至少') }">{{ pwdMsg }}</p>
      <button class="btn" :disabled="savingPwd" @click="changePassword">{{ savingPwd ? '提交中…' : '修改密码' }}</button>
    </div>
  </section>
</template>
