<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useConfirm } from '../../composables/useConfirm'

const confirmDlg = useConfirm()

const current = reactive({
  type: 'sqlite',
  database: '',
  host: '',
  port: '',
  username: '',
  configured: false,
  drivers: {},
})
const form = reactive({
  type: 'sqlite',
  host: '',
  port: '',
  database: '',
  username: '',
  password: '',
  path: './app.db',
})
const msg = ref('')
const busy = ref(false)
const switching = ref(false)

const typeOptions = [
  { value: 'sqlite', label: 'SQLite' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mssql', label: 'SQL Server (MSSQL)' },
  { value: 'oracle', label: 'Oracle' },
]

const isSqlite = computed(() => form.type === 'sqlite')

function typeLabel(t) {
  const o = typeOptions.find((x) => x.value === t)
  return o ? o.label : t
}

function buildBody() {
  const body = {
    type: form.type,
    ...(isSqlite.value ? { path: form.path } : { host: form.host, port: form.port, database: form.database, username: form.username, password: form.password }),
  }
  return body
}

async function load() {
  try {
    const r = await api.adminDb()
    Object.assign(current, r)
    if (r.type === 'sqlite') form.path = r.database || './app.db'
    else {
      form.host = r.host || ''
      form.port = r.port || ''
      form.database = r.database || ''
      form.username = r.username || ''
    }
  } catch (e) {
    msg.value = '加载数据库信息失败'
  }
}

async function testConn() {
  busy.value = true
  msg.value = ''
  try {
    const r = await api.adminDbTest(buildBody())
    msg.value = `连接成功：${typeLabel(r.dialect)}`
  } catch (e) {
    msg.value = e.message
  } finally {
    busy.value = false
  }
}

async function doSwitch() {
  const ok = await confirmDlg.askConfirm(
    `即将把当前数据迁移并切换到 ${typeLabel(form.type)}。\n\n此操作会复制当前所有数据到目标库，成功后立即生效。是否继续？`,
    { title: '迁移并切换数据库', danger: true },
  )
  if (!ok) return
  switching.value = true
  msg.value = ''
  try {
    const r = await api.adminDbSwitch(buildBody())
    msg.value = `迁移并切换成功：${typeLabel(r.dialect)}`
    await load()
  } catch (e) {
    msg.value = e.message
  } finally {
    switching.value = false
  }
}

async function backup() {
  busy.value = true
  msg.value = ''
  try {
    const r = await api.adminDbBackup()
    msg.value = r.message
  } catch (e) {
    msg.value = e.message
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="content">
    <h2>数据库</h2>

    <div class="card" style="margin-bottom: 18px">
      <h3 style="margin-bottom: 12px">当前数据库</h3>
      <div class="sms-grid">
        <label>类型
          <input class="input" :value="typeLabel(current.type)" disabled />
        </label>
        <label>数据库 / 路径
          <input class="input" :value="current.database" disabled />
        </label>
        <label v-if="current.type !== 'sqlite'">主机
          <input class="input" :value="current.host" disabled />
        </label>
        <label v-if="current.type !== 'sqlite'">端口
          <input class="input" :value="current.port" disabled />
        </label>
      </div>
      <p class="hint" style="margin-top: 10px">
        配置来源：<span>{{ current.configured ? 'data/db_config.json' : '环境变量 DATABASE_URL（默认 SQLite）' }}</span>
      </p>
      <div class="ops" style="margin-top: 12px">
        <button class="btn btn-test" :disabled="busy" @click="backup">备份当前库</button>
      </div>
    </div>

    <div class="card">
      <h3 style="margin-bottom: 12px">切换数据库</h3>
      <div class="sms-grid">
        <label>数据库类型
          <select v-model="form.type" class="input">
            <option v-for="o in typeOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </label>
        <label v-if="isSqlite">SQLite 文件路径
          <input v-model="form.path" class="input" placeholder="./app.db" />
        </label>
        <template v-else>
          <label>主机
            <input v-model="form.host" class="input" placeholder="127.0.0.1" />
          </label>
          <label>端口
            <input v-model="form.port" class="input" placeholder="3306" />
          </label>
          <label>数据库名
            <input v-model="form.database" class="input" placeholder="askaibot" />
          </label>
          <label>用户名
            <input v-model="form.username" class="input" placeholder="root" />
          </label>
          <label>密码
            <input v-model="form.password" type="password" class="input" placeholder="密码" />
          </label>
        </template>
      </div>

      <div class="ops" style="margin-top: 14px">
        <button class="btn btn-test" :disabled="busy" @click="testConn">测试连接</button>
        <button class="btn btn-edit" :disabled="switching" @click="doSwitch">{{ switching ? '切换中…' : '迁移并切换' }}</button>
      </div>

      <div class="ops" style="margin-top: 12px">
        <span v-for="(ok, k) in current.drivers" :key="k" class="hint" :class="{ 'hint-danger': !ok }" style="margin-right: 14px">
          {{ typeLabel(k) }}：{{ ok ? '已安装' : '未安装' }}
        </span>
      </div>

      <p v-if="msg" class="hint" style="margin-top: 12px">{{ msg }}</p>
      <p class="hint" style="margin-top: 12px">
        切换会将当前所有数据（用户/会话/消息/配置等）完整迁移到目标库，成功后免重启立即生效并持久化。上传的附件文件不迁移（仍保存在服务器）。目标库已存在非空表时会拒绝，如需覆盖请确认后重试。
      </p>
    </div>

    <ConfirmDialog
      :visible="confirmDlg.visible"
      :title="confirmDlg.title"
      :message="confirmDlg.message"
      :danger="confirmDlg.danger"
      @confirm="confirmDlg.confirm"
      @cancel="confirmDlg.cancel"
    />
  </section>
</template>
