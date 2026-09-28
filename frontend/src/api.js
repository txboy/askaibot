import { store } from './store'

const BASE = '/api'

async function request(path, { method = 'GET', body, headers = {}, token } = {}) {
  const h = { ...headers }
  const t = token !== undefined ? token : store.token
  if (t) h['Authorization'] = `Bearer ${t}`
  if (body !== undefined) h['Content-Type'] = 'application/json'

  const res = await fetch(BASE + path, {
    method,
    headers: h,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    let msg = `请求失败 (${res.status})`
    try {
      const j = await res.json()
      if (j.detail) msg = typeof j.detail === 'string' ? j.detail : String(j.detail)
    } catch {}
    throw new Error(msg)
  }
  return res.json()
}

const adminRequest = (path, opts = {}) => request(path, { ...opts, token: store.adminToken })

export const api = {
  smsSend: (phone) => request('/auth/sms/send', { method: 'POST', body: { phone } }),
  smsVerify: (phone, code) => request('/auth/sms/verify', { method: 'POST', body: { phone, code } }),
  wecomQrcode: () => request('/auth/wecom/qrcode'),
  dingtalkQrcode: () => request('/auth/dingtalk/qrcode'),
  dingtalkFreeLogin: (code) => request('/auth/dingtalk/free-login', { method: 'POST', body: { code } }),
  feishuQrcode: () => request('/auth/feishu/qrcode'),
  feishuFreeLogin: (code) => request('/auth/feishu/free-login', { method: 'POST', body: { code } }),
  me: () => request('/auth/me'),
  updateProfile: (data) => request('/auth/profile', { method: 'PUT', body: data }),
  updatePhone: (phone, code) => request('/auth/phone', { method: 'PUT', body: { phone, code } }),
  uploadAvatar: (file, target = 'user') => {
    const form = new FormData()
    form.append('file', file)
    return fetch(BASE + `/auth/avatar?target=${encodeURIComponent(target)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${store.token}` },
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        let msg = `上传失败 (${res.status})`
        try {
          const j = await res.json()
          if (j.detail) msg = String(j.detail)
        } catch {}
        throw new Error(msg)
      }
      return res.json()
    })
  },
  uploadAssistantAvatar: (file) => api.uploadAvatar(file, 'assistant'),

  conversations: () => request('/conversations'),
  createConversation: (data) => request('/conversations', { method: 'POST', body: data }),
  renameConversation: (id, title) => request(`/conversations/${id}`, { method: 'PUT', body: { title } }),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: 'DELETE' }),
  messages: (id) => request(`/conversations/${id}/messages`),
  updateConversationMcp: (id, mcpIds) => request(`/conversations/${id}/mcp`, { method: 'PUT', body: { mcp_ids: mcpIds } }),
  updateConversationSkills: (id, skillIds) => request(`/conversations/${id}/skills`, { method: 'PUT', body: { skill_ids: skillIds } }),

  endpoints: () => request('/endpoints'),
  knowledgeBases: () => request('/knowledge-bases'),
  mcpServers: () => request('/mcp'),
  skills: () => request('/skills'),

  getTheme: () => request('/config/theme'),
  getDebug: () => request('/config/debug'),
  getSms: () => request('/config/sms'),
  getWecom: () => request('/config/wecom'),
  getDingtalk: () => request('/config/dingtalk'),
  getFeishu: () => request('/config/feishu'),
  getSearch: () => request('/config/search'),
  site: () => request('/config/site'),

  adminLogin: (username, password) => request('/admin/login', { method: 'POST', body: { username, password } }),
  adminAccess: async (r) => {
    const res = await fetch(`${BASE}/admin/access?r=${encodeURIComponent(r || '')}`)
    return res.ok
  },
  adminEndpoints: () => adminRequest('/admin/endpoints'),
  adminCreateEndpoint: (data) => adminRequest('/admin/endpoints', { method: 'POST', body: data }),
  adminUpdateEndpoint: (id, data) => adminRequest(`/admin/endpoints/${id}`, { method: 'PUT', body: data }),
  adminDeleteEndpoint: (id) => adminRequest(`/admin/endpoints/${id}`, { method: 'DELETE' }),
  adminGetWecom: () => adminRequest('/admin/wecom'),
  adminSaveWecom: (data) => adminRequest('/admin/wecom', { method: 'PUT', body: data }),
  adminGetDingtalk: () => adminRequest('/admin/dingtalk'),
  adminSaveDingtalk: (data) => adminRequest('/admin/dingtalk', { method: 'PUT', body: data }),
  adminGetFeishu: () => adminRequest('/admin/feishu'),
  adminSaveFeishu: (data) => adminRequest('/admin/feishu', { method: 'PUT', body: data }),
  adminGetLogo: () => adminRequest('/admin/logo'),
  adminDeleteLogo: () => adminRequest('/admin/logo', { method: 'DELETE' }),
  adminStats: () => adminRequest('/admin/stats'),
  adminEndpointsUsage: () => adminRequest('/admin/endpoints/usage'),
  adminGetTheme: () => adminRequest('/admin/theme'),
  adminSaveTheme: (theme) => adminRequest('/admin/theme', { method: 'PUT', body: { theme } }),
  adminGetDebug: () => adminRequest('/admin/debug'),
  adminSaveDebug: (debug) => adminRequest('/admin/debug', { method: 'PUT', body: { debug_mode: debug } }),
  adminGetSystem: () => adminRequest('/admin/system'),
  adminSaveSystem: (data) => adminRequest('/admin/system', { method: 'PUT', body: data }),
  adminDeleteFavicon: () => adminRequest('/admin/favicon', { method: 'DELETE' }),
  adminUploadAssistantAvatar: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(BASE + '/admin/assistant-avatar', {
      method: 'POST',
      headers: { Authorization: `Bearer ${store.adminToken}` },
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        let msg = `上传失败 (${res.status})`
        try {
          const j = await res.json()
          if (j.detail) msg = String(j.detail)
        } catch {}
        throw new Error(msg)
      }
      return res.json()
    })
  },
  adminDeleteAssistantAvatar: () => adminRequest('/admin/assistant-avatar', { method: 'DELETE' }),
  adminGetSms: () => adminRequest('/admin/sms'),
  adminSaveSms: (data) => adminRequest('/admin/sms', { method: 'PUT', body: data }),
  adminGetSearch: () => adminRequest('/admin/search'),
  adminSaveSearch: (data) => adminRequest('/admin/search', { method: 'PUT', body: data }),
  adminGetKnowledgeBases: () => adminRequest('/admin/knowledge-bases'),
  adminCreateKnowledgeBase: (data) => adminRequest('/admin/knowledge-bases', { method: 'POST', body: data }),
  adminUpdateKnowledgeBase: (id, data) => adminRequest(`/admin/knowledge-bases/${id}`, { method: 'PUT', body: data }),
  adminDeleteKnowledgeBase: (id) => adminRequest(`/admin/knowledge-bases/${id}`, { method: 'DELETE' }),
  adminTestKnowledgeBase: (data) => adminRequest('/admin/knowledge-bases/test', { method: 'POST', body: data }),
  adminGetWecomBots: (provider = 'wecom') => adminRequest(`/admin/wecom-bots?provider=${provider}`),
  adminCreateWecomBot: (data) => adminRequest('/admin/wecom-bots', { method: 'POST', body: data }),
  adminUpdateWecomBot: (id, data) => adminRequest(`/admin/wecom-bots/${id}`, { method: 'PUT', body: data }),
  adminDeleteWecomBot: (id) => adminRequest(`/admin/wecom-bots/${id}`, { method: 'DELETE' }),
  adminMcpServers: () => adminRequest('/admin/mcp'),
  adminCreateMcp: (data) => adminRequest('/admin/mcp', { method: 'POST', body: data }),
  adminUpdateMcp: (id, data) => adminRequest(`/admin/mcp/${id}`, { method: 'PUT', body: data }),
  adminDeleteMcp: (id) => adminRequest(`/admin/mcp/${id}`, { method: 'DELETE' }),
  adminTestMcp: (id) => adminRequest(`/admin/mcp/${id}/test`, { method: 'POST' }),
  adminRefreshMcp: (id) => adminRequest(`/admin/mcp/${id}/refresh`, { method: 'POST' }),
  adminSkills: () => adminRequest('/admin/skills'),
  adminUploadSkill: (file, scope = 'global', enabled = 1) => {
    const form = new FormData()
    form.append('file', file)
    form.append('scope', scope)
    form.append('enabled', String(enabled))
    return fetch(BASE + '/admin/skills', {
      method: 'POST',
      headers: { Authorization: `Bearer ${store.adminToken}` },
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        let msg = `上传失败 (${res.status})`
        try {
          const j = await res.json()
          if (j.detail) msg = String(j.detail)
        } catch {}
        throw new Error(msg)
      }
      return res.json()
    })
  },
  adminUpdateSkill: (id, data) => adminRequest(`/admin/skills/${id}`, { method: 'PUT', body: data }),
  adminDeleteSkill: (id) => adminRequest(`/admin/skills/${id}`, { method: 'DELETE' }),
  adminTestSkill: (id, tool, args = {}) => adminRequest(`/admin/skills/${id}/test`, { method: 'POST', body: { tool, args } }),
  adminUsers: () => adminRequest('/admin/users'),
  adminDeleteUser: (id) => adminRequest(`/admin/users/${id}`, { method: 'DELETE' }),
  adminChangePassword: (data) => adminRequest('/admin/password', { method: 'PUT', body: data }),
  adminUploadLogo: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(BASE + '/admin/logo', {
      method: 'POST',
      headers: { Authorization: `Bearer ${store.adminToken}` },
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        let msg = `上传失败 (${res.status})`
        try {
          const j = await res.json()
          if (j.detail) msg = String(j.detail)
        } catch {}
        throw new Error(msg)
      }
      return res.json()
    })
  },
  adminUploadFavicon: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(BASE + '/admin/favicon', {
      method: 'POST',
      headers: { Authorization: `Bearer ${store.adminToken}` },
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        let msg = `上传失败 (${res.status})`
        try {
          const j = await res.json()
          if (j.detail) msg = String(j.detail)
        } catch {}
        throw new Error(msg)
      }
      return res.json()
    })
  },
}

export function authFetchBlob(id) {
  return fetch(`${BASE}/files/${id}`, {
    headers: { Authorization: `Bearer ${store.token}` },
  }).then(async (res) => {
    if (!res.ok) throw new Error('加载文件失败')
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  })
}

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${store.token}` },
    body: form,
  })
  if (!res.ok) {
    let msg = `上传失败 (${res.status})`
    try {
      const j = await res.json()
      if (j.detail) msg = String(j.detail)
    } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export async function streamChat({ conversationId, content, attachmentIds = [], endpointId, model, webSearch = false, knowledgeBaseId = null, onDelta, onError, onDone, onStatus }) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${store.token}`,
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      content,
      attachment_ids: attachmentIds,
      endpoint_id: endpointId,
      model,
      web_search: webSearch,
      knowledge_base_id: knowledgeBaseId,
    }),
  })

  if (!res.ok) {
    let msg = `请求失败 (${res.status})`
    try {
      const j = await res.json()
      if (j.detail) msg = String(j.detail)
    } catch {}
    throw new Error(msg)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, idx).trim()
      buffer = buffer.slice(idx + 1)
      if (!line.startsWith('data:')) continue
      let obj
      try {
        obj = JSON.parse(line.slice(5).trim())
      } catch {
        continue
      }
      if (obj.delta) onDelta(obj.delta)
      if (obj.error) onError(obj.error)
      if (obj.status && onStatus) onStatus(obj.status)
      if (obj.done) onDone()
    }
  }
}
