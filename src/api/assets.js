import { api } from './client';

export const assetsApi = {
  async getAssets(filters = {}) {
    return api.get('/api/assets', filters);
  },

  async getAsset(assetId) {
    return api.get(`/api/assets/${assetId}`);
  },

  async createAsset(assetData) {
    return api.post('/api/assets', assetData);
  },

  async updateAsset(assetId, updateData) {
    return api.patch(`/api/assets/${assetId}`, updateData);
  },

  async deleteAsset(assetId) {
    return api.delete(`/api/assets/${assetId}`);
  },
};
