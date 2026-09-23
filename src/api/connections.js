import { api } from './client';

export const connectionsApi = {
  async getConnections() {
    return api.get('/api/connections');
  },

  async getConnection(id) {
    return api.get(`/api/connections/${id}`);
  },

  async createConnection(payload) {
    return api.post('/api/connections', payload);
  },

  async disconnectConnection(id, purgeData = false) {
    return api.delete(`/api/connections/${id}${purgeData ? '?purge_data=true' : ''}`);
  },

  async syncConnection(id) {
    return api.post(`/api/connections/${id}/sync`);
  },

  async getConnectionStatus(id) {
    return api.get(`/api/connections/${id}/status`);
  },

  async testConnection(payload) {
    return api.post('/api/connections/test', payload);
  },
};
