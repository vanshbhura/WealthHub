import { api } from './client';

export const portfolioApi = {
  async getSummary() {
    return api.get('/api/portfolio/summary');
  },

  async getConnectedPlatforms() {
    return api.get('/api/portfolio/platforms');
  },

  async getAssets(params = {}) {
    return api.get('/api/portfolio/assets', params);
  },

  async getSnapshots(period = '1M', envelope = true) {
    return api.get('/api/portfolio/snapshots', { period, envelope });
  },

  async getAllocation() {
    return api.get('/api/portfolio/allocation');
  },

  async captureSnapshot() {
    return api.post('/api/portfolio/snapshots/capture');
  },
};
