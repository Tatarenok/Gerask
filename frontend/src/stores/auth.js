import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token')
  }),
  
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.role?.is_admin || false
  },
  
  actions: {
    async login(login, password) {
      const response = await api.post('/auth/login', { login, password })
      this.token = response.data.access_token
      localStorage.setItem('token', this.token)
      await this.fetchUser()
    },
    
    async fetchUser() {
      const response = await api.get('/auth/me')
      this.user = response.data
    },
    
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
    }
  }
})
