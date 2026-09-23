import { authApi } from './auth';

const BASE_URL = 'http://localhost:8000';

function getAuthHeaders(isFormData = false) {
  const token = authApi.getToken();
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  return headers;
}

export const importsApi = {
  /**
   * Uploads and parses statement file (CSV, XLSX, PDF).
   * @param {FormData} formData - Contains file, platform_id, import_type
   */
  async uploadStatement(formData) {
    const res = await fetch(`${BASE_URL}/api/imports`, {
      method: 'POST',
      headers: getAuthHeaders(true),
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.message || 'Failed to upload statement');
    }
    return res.json();
  },

  /**
   * Retrieves import job metadata and status.
   */
  async getImport(importId) {
    const res = await fetch(`${BASE_URL}/api/imports/${importId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to fetch import status');
    }
    return res.json();
  },

  /**
   * Retrieves detailed preview data, rows, and validation issues.
   */
  async getPreview(importId) {
    const res = await fetch(`${BASE_URL}/api/imports/${importId}/preview`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to fetch import preview');
    }
    return res.json();
  },

  /**
   * Updates column mapping and re-validates statement rows.
   */
  async updateMapping(importId, columnMapping) {
    const res = await fetch(`${BASE_URL}/api/imports/${importId}/map`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ column_mapping: columnMapping }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to update column mapping');
    }
    return res.json();
  },

  /**
   * Re-validates statement against current mappings.
   */
  async validateImport(importId) {
    const res = await fetch(`${BASE_URL}/api/imports/${importId}/validate`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to re-validate statement');
    }
    return res.json();
  },

  /**
   * Atomically commits the validated import job.
   */
  async commitImport(importId) {
    const res = await fetch(`${BASE_URL}/api/imports/${importId}/commit`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to commit statement');
    }
    return res.json();
  },

  /**
   * Cancels/deletes an uncommitted import job.
   */
  async cancelImport(importId) {
    const res = await fetch(`${BASE_URL}/api/imports/${importId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok && res.status !== 204) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to cancel import');
    }
    return true;
  },

  /**
   * Fetches user's import history.
   */
  async getHistory() {
    const res = await fetch(`${BASE_URL}/api/imports`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to load import history');
    }
    return res.json();
  },
};
