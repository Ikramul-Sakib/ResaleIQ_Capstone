import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import api from './api'
import { useAuthStore } from './stores/auth'
import './styles.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// An expired or revoked token logs the user out and sends them to the login page.
api.interceptors.response.use(undefined, (error) => {
  const auth = useAuthStore()
  if (error.response?.status === 401 && auth.user) {
    auth.logout()
    const current = router.currentRoute.value
    if (current.meta.auth || current.meta.admin) {
      router.push({ name: 'login', query: { redirect: current.fullPath } })
    }
  }
  return Promise.reject(error)
})

app.mount('#app')
