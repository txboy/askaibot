<script setup>
import { ref, onMounted } from 'vue'

const fid = 'lg' + Math.random().toString(36).slice(2, 8)
const customLogo = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/logo?t=' + Date.now())
    if (res.ok) {
      const blob = await res.blob()
      customLogo.value = URL.createObjectURL(blob)
    }
  } catch {}
})
</script>

<template>
  <img v-if="customLogo" class="brand-logo custom-logo" :src="customLogo" alt="logo" />
  <svg
    v-else
    class="brand-logo"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 1794 820"
    width="100%"
  >
    <defs>
      <filter :id="fid" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="var(--primary)" flood-opacity="0.35" />
      </filter>
    </defs>
    <g :filter="`url(#${fid})`">
      <text x="-11" y="460" class="gila-main">a</text>
      <text x="399" y="460" class="gila-main">s</text>
      <text x="786" y="460" class="gila-main-bold">k</text>
      <text x="1205" y="460" class="gila-main">a</text>
      <text x="1614" y="460" class="gila-main-bold">i</text>

      <circle cx="155" cy="334" r="30" class="dot" />
      <circle cx="1371" cy="334" r="30" class="dot" />
    </g>
    <text x="897" y="640" text-anchor="middle" class="gila-sub">ARTIFICIAL INTELLIGENCE</text>
    <line class="deco" x1="240" y1="720" x2="880" y2="720" />
    <polygon class="deco-fill" points="900,695 925,720 900,745 875,720" />
    <line class="deco" x1="925" y1="720" x2="1565" y2="720" />
  </svg>
</template>

<style scoped>
.brand-logo {
  display: block;
}

.custom-logo {
  max-width: 100%;
  height: auto;
  object-fit: contain;
}

.gila-main {
  font-family: 'ZiHunBianTaoTi-2', sans-serif;
  font-weight: 400;
  font-size: 600px;
  fill: var(--primary);
  stroke: none;
}

.gila-main-bold {
  font-family: 'ZiHunBianTaoTi-2', sans-serif;
  font-weight: 700;
  font-size: 600px;
  fill: var(--primary-hover);
  stroke: none;
}

.gila-sub {
  font-family: 'ZiHunBianTaoTi-2', sans-serif;
  font-weight: 600;
  font-size: 76px;
  fill: var(--primary);
  stroke: none;
  letter-spacing: 16px;
  opacity: 0.85;
}

.dot {
  fill: var(--primary-hover);
}

.deco {
  stroke: var(--primary);
  stroke-width: 6;
}

.deco-fill {
  fill: var(--primary);
}
</style>
