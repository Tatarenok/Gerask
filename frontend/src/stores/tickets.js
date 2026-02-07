import { defineStore } from 'pinia'
import api from '../api'

export const useTicketsStore = defineStore('tickets', {
  state: () => ({
    tickets: [],
    currentTicket: null,
    loading: false
  }),
  
  actions: {
    async fetchMyTickets() {
      this.loading = true
      const response = await api.get('/tickets/my')
      this.tickets = response.data
      this.loading = false
    },
    
    async fetchAllTickets() {
      this.loading = true
      const response = await api.get('/tickets')
      this.tickets = response.data
      this.loading = false
    },
    
    async fetchTicket(key) {
      const response = await api.get('/tickets/' + key)
      this.currentTicket = response.data
      return response.data
    },
    
    async createTicket(data) {
      const response = await api.post('/tickets', data)
      this.tickets.unshift(response.data)
      return response.data
    },
    
    async updateTicketStatus(key, status) {
      const response = await api.patch('/tickets/' + key + '/status', { status })
      this.currentTicket = response.data
      return response.data
    }
  }
})
