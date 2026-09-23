import { api } from './client';

export const accountAggregatorApi = {
  /**
   * Initiates a sandbox consent session via Setu AA.
   */
  async createConsent(payload = {}) {
    return api.post('/api/account-aggregator/consent', payload);
  },

  /**
   * Retrieves current authorization status for a consent request.
   */
  async getConsentStatus(consentId) {
    return api.get(`/api/account-aggregator/consent/${consentId}`);
  },

  /**
   * Ingests sandbox financial data for an authorized consent session.
   */
  async syncConsentData(consentId) {
    return api.post(`/api/account-aggregator/consent/${consentId}/sync`);
  },

  /**
   * Returns connection & consent status for an Account Aggregator connection.
   */
  async getConnectionStatus(connectionId) {
    return api.get(`/api/account-aggregator/${connectionId}/status`);
  },

  /**
   * Disconnects Account Aggregator connection.
   */
  async disconnectConnection(connectionId) {
    return api.post(`/api/account-aggregator/${connectionId}/disconnect`);
  },
};
