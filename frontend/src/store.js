import { reactive } from 'vue'

export const store = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  adminToken: localStorage.getItem('admin_token') || '',

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

  logoutAdmin() {
    this.adminToken = ''
    localStorage.removeItem('admin_token')
  },
})
