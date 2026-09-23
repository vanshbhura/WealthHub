import { api } from './client';

export const authApi = {
  async register(email, password, fullName) {
    const data = await api.post('/api/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    api.setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async login(email, password) {
    const data = await api.post('/api/auth/login', {
      email,
      password,
    });
    api.setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async getMe() {
    return api.get('/api/auth/me');
  },

  logout() {
    api.clearTokens();
  },

  isAuthenticated() {
    return !!api.getToken();
  },
};
