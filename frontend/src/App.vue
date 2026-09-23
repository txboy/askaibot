<script setup>
import { onMounted } from 'vue'
import { api } from './api'
import { applyTheme } from './theme'

function setFavicon(url) {
  let link = document.querySelector("link[rel~='icon']")
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = url
}

onMounted(async () => {
  try {
    const r = await api.getTheme()
    applyTheme(r.theme)
  } catch {}
  try {
    const s = await api.site()
    if (s.site_title) document.title = s.site_title
    if (s.favicon_url) setFavicon(s.favicon_url)
  } catch {}
})
</script>

<template>
  <router-view />
</template>
