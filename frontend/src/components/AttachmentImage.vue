<script setup>
import { ref, onMounted } from 'vue'
import { authFetchBlob } from '../api'

const props = defineProps({ id: [Number, String] })
const src = ref('')

onMounted(async () => {
  try {
    src.value = await authFetchBlob(props.id)
  } catch {
    src.value = ''
  }
})
</script>

<template>
  <img v-if="src" :src="src" class="att-img" />
</template>

<style scoped>
.att-img {
  max-width: 200px;
  max-height: 200px;
  border-radius: 8px;
  border: 1px solid var(--border);
  display: block;
  margin-top: 6px;
}
</style>
