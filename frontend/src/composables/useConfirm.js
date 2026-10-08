import { ref, reactive } from 'vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

export function useConfirm() {
  const visible = ref(false)
  const title = ref('确认操作')
  const message = ref('')
  const danger = ref(false)
  let resolver = null

  function askConfirm(msg, opts = {}) {
    message.value = msg
    title.value = opts.title || '确认操作'
    danger.value = !!opts.danger
    visible.value = true
    return new Promise((resolve) => {
      resolver = resolve
    })
  }

  function confirm() {
    visible.value = false
    if (resolver) resolver(true)
    resolver = null
  }

  function cancel() {
    visible.value = false
    if (resolver) resolver(false)
    resolver = null
  }

  return reactive({ visible, title, message, danger, askConfirm, confirm, cancel })
}
