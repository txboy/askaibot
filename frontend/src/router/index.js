import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Chat from '../views/Chat.vue'
import Admin from '../views/Admin.vue'
import NotFound from '../views/NotFound.vue'
import { store } from '../store'
import { api } from '../api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Chat, meta: { requiresAuth: true } },
    { path: '/login', component: Login },
    { path: '/admin', component: Admin },
    { path: '/404', component: NotFound },
    { path: '/:pathMatch(.*)*', component: NotFound },
  ],
})

function isWecom() {
  return /wxwork/i.test(navigator.userAgent)
}

router.beforeEach(async (to) => {
  if (to.path === '/admin') {
    const ok = await api.adminAccess(String(to.query.r || ''))
    if (!ok) return '/404'
  }
  if (to.meta.requiresAuth && !store.token) {
    if (isWecom()) {
      window.location.replace('/api/auth/wecom/oauth')
      return false
    }
    return '/login'
  }
  if (to.path === '/login' && store.token) return '/'
})

export default router
