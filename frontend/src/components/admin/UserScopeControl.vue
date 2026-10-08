<script setup>
import { ref, onMounted, watch } from 'vue'
import { api } from '../../api'

const props = defineProps({
  scope: { type: String, default: 'global' },
  groups: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:scope', 'update:groups'])

const allGroups = ref([])
const scopes = [
  { value: 'global', label: '全部用户' },
  { value: 'group', label: '按组授权' },
]

async function loadGroups() {
  try {
    allGroups.value = await api.adminGroups()
  } catch {
    allGroups.value = []
  }
}

function toggleGroup(gid) {
  const arr = [...props.groups]
  const idx = arr.indexOf(gid)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(gid)
  emit('update:groups', arr)
}

onMounted(loadGroups)
</script>

<template>
  <label>可见范围
    <select :value="scope" class="input" @change="emit('update:scope', $event.target.value)">
      <option v-for="s in scopes" :key="s.value" :value="s.value">{{ s.label }}</option>
    </select>
  </label>
  <label v-if="scope === 'group'">
    授权用户组
    <div class="kb-checkbox-list">
      <label v-for="g in allGroups" :key="g.id" class="check">
        <input type="checkbox" :value="g.id" :checked="groups.includes(g.id)" @change="toggleGroup(g.id)" />
        {{ g.name }}
      </label>
      <span v-if="!allGroups.length" class="hint">暂无用户组，请先到「用户组」页创建</span>
    </div>
  </label>
</template>
