import { defineStore } from 'pinia'
import api, { tokenStorage } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    ready: false,
    unreadMessages: 0,
    unreadNotifications: 0,
    cartCount: 0,
    pendingSales: 0,
  }),

  getters: {
    isLoggedIn: (state) => !!state.user,
    isAdmin: (state) => state.user?.role === 'admin',
  },

  actions: {
    async init() {
      if (this.ready) return
      if (tokenStorage.get()) {
        try {
          const { data } = await api.get('/auth/me')
          this.user = data.user
          this.refreshSummary()
        } catch {
          tokenStorage.clear()
        }
      }
      this.ready = true
    },

    setSession({ token, user }) {
      tokenStorage.set(token)
      this.user = user
      this.refreshSummary()
    },

    async login(email, password) {
      const { data } = await api.post('/auth/login', { email, password })
      this.setSession(data)
    },

    async register(payload) {
      const { data } = await api.post('/auth/register', payload)
      this.setSession(data)
    },

    logout() {
      tokenStorage.clear()
      this.user = null
      this.unreadMessages = 0
      this.unreadNotifications = 0
      this.cartCount = 0
      this.pendingSales = 0
    },

    async refreshSummary() {
      if (!this.user) return
      try {
        const { data } = await api.get('/notifications/summary')
        this.unreadMessages = data.unread_messages
        this.unreadNotifications = data.unread_notifications
        this.cartCount = data.cart_count
        this.pendingSales = data.pending_sales
      } catch {
        /* badge counts are not critical */
      }
    },
  },
})
