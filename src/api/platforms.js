import { api } from './client';

export const platformsApi = {
  async getPlatforms(category = null) {
    const params = category && category !== 'All' ? { category: category.toUpperCase() } : {};
    return api.get('/api/platforms', params);
  },

  async getPlatform(platformId) {
    return api.get(`/api/platforms/${platformId}`);
  },

  async getPlatformConnectors(platformId) {
    return api.get(`/api/platforms/${platformId}/connectors`);
  },
};
