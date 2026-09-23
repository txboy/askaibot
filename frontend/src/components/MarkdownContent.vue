<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { renderMarkdown } from '../utils/markdown'

const props = defineProps({ content: String })

const root = ref(null)
const html = computed(() => renderMarkdown(props.content))

async function decorate() {
  await nextTick()
  const el = root.value
  if (!el) return
  el.querySelectorAll('pre').forEach((pre) => {
    if (pre.parentElement?.classList.contains('code-wrap')) return
    const code = pre.querySelector('code')
    if (code) code.classList.add('hljs')

    const wrap = document.createElement('div')
    wrap.className = 'code-wrap'

    const head = document.createElement('div')
    head.className = 'code-head'

    const langMatch = code?.className.match(/language-(\w+)/)
    const lang = langMatch ? langMatch[1] : ''

    const langSpan = document.createElement('span')
    langSpan.className = 'code-lang'
    langSpan.textContent = lang

    const btn = document.createElement('button')
    btn.className = 'copy-btn'
    btn.type = 'button'
    btn.textContent = '复制'

    head.appendChild(langSpan)
    head.appendChild(btn)

    pre.parentNode.insertBefore(wrap, pre)
    wrap.appendChild(head)
    wrap.appendChild(pre)
  })
}

watch(() => props.content, decorate, { flush: 'post' })
onMounted(decorate)

function onClick(e) {
  const btn = e.target.closest('.copy-btn')
  if (!btn) return
  const code = btn.closest('.code-wrap')?.querySelector('code')
  if (!code) return
  navigator.clipboard.writeText(code.textContent || '')
  btn.textContent = '已复制'
  setTimeout(() => {
    btn.textContent = '复制'
  }, 1500)
}
</script>

<template>
  <div ref="root" class="md-body" v-html="html" @click="onClick"></div>
</template>
