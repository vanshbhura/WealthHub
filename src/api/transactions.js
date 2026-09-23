import { api } from './client';

export const transactionsApi = {
  async getTransactions(params = {}) {
    return api.get('/api/transactions', params);
  },

  async getTransaction(transactionId) {
    return api.get(`/api/transactions/${transactionId}`);
  },

  async createTransaction(transactionData) {
    return api.post('/api/transactions', transactionData);
  },
};
