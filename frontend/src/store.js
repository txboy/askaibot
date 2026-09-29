import { reactive } from 'vue'

export const store = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  adminToken: localStorage.getItem('admin_token') || '',
  adminRole: localStorage.getItem('admin_role') || '',

  setAuth(token, user) {
    this.token = token
    this.user = user
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
  },

  setUser(user) {
    this.user = user
    localStorage.setItem('user', JSON.stringify(user))
  },

  logout() {
    this.token = ''
    this.user = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  },

  setAdminToken(token) {
    this.adminToken = token
    localStorage.setItem('admin_token', token)
  },

  setAdminRole(role) {
    this.adminRole = role || ''
    localStorage.setItem('admin_role', role || '')
  },

  logoutAdmin() {
    this.adminToken = ''
    this.adminRole = ''
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_role')
  },
})
