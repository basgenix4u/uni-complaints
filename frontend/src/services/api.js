import axios from 'axios';

// Relative by default so the browser calls the origin it was served from
// and the dev server or reverse proxy forwards to the API. An absolute
// URL is only needed when the API is on a different host in production.
export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export const tokens = {
  get access() {
    return localStorage.getItem('access_token');
  },
  get refresh() {
    return localStorage.getItem('refresh_token');
  },
  set({ access_token, refresh_token }) {
    if (access_token) localStorage.setItem('access_token', access_token);
    if (refresh_token) localStorage.setItem('refresh_token', refresh_token);
  },
  clear() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

api.interceptors.request.use((config) => {
  const token = tokens.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// A single refresh is shared between concurrent 401s so that a burst of
// parallel requests does not trigger several refresh calls.
let refreshing = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    if (status !== 401 || original?._retried || original?.url?.includes('/auth/')) {
      return Promise.reject(error);
    }

    if (!tokens.refresh) {
      tokens.clear();
      return Promise.reject(error);
    }

    original._retried = true;

    refreshing =
      refreshing ||
      axios
        .post(`${API_BASE_URL}/auth/refresh`, {}, {
          headers: { Authorization: `Bearer ${tokens.refresh}` },
        })
        .then((response) => {
          const token = response.data?.data?.access_token;
          tokens.set({ access_token: token });
          return token;
        })
        .catch((refreshError) => {
          tokens.clear();
          throw refreshError;
        })
        .finally(() => {
          refreshing = null;
        });

    try {
      const token = await refreshing;
      original.headers.Authorization = `Bearer ${token}`;
      return api(original);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    }
  },
);

/** Unwraps the `{ success, message, data }` envelope the API returns. */
const unwrap = (response) => response.data?.data ?? {};

/** Extracts a message suitable for showing to a user. */
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (error?.code === 'ERR_NETWORK') {
    return "You appear to be offline. Check your connection and try again.";
  }
  return error?.response?.data?.message || fallback;
}

/** Field-level validation errors, keyed by field name. */
export function fieldErrors(error) {
  return error?.response?.data?.errors || {};
}

export const authService = {
  register: (data) => api.post('/auth/register', data).then(unwrap),
  login: (data) => api.post('/auth/login', data).then(unwrap),
  me: () => api.get('/auth/me').then(unwrap),
  updateProfile: (data) => api.put('/auth/profile', data).then(unwrap),
  changePassword: (data) => api.post('/auth/change-password', data).then(unwrap),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }).then(unwrap),
  resetPassword: (token, password) =>
    api.post('/auth/reset-password', { token, password }).then(unwrap),
};

export const publicService = {
  institutions: () => api.get('/public/institutions').then(unwrap),
  track: (ticket) => api.get(`/public/track/${encodeURIComponent(ticket)}`).then(unwrap),
};

export const complaintService = {
  list: (params) => api.get('/complaints', { params }).then(unwrap),
  get: (id) => api.get(`/complaints/${id}`).then(unwrap),
  create: (data) => api.post('/complaints', data).then(unwrap),
  reply: (id, data) => api.post(`/complaints/${id}/responses`, data).then(unwrap),
  setStatus: (id, data) => api.put(`/complaints/${id}/status`, data).then(unwrap),
  setPriority: (id, data) => api.put(`/complaints/${id}/priority`, data).then(unwrap),
  assign: (id, data) => api.put(`/complaints/${id}/assign`, data).then(unwrap),
  rate: (id, rating) => api.post(`/complaints/${id}/rate`, { rating }).then(unwrap),
};

export const attachmentService = {
  upload: (complaintId, file, isInternal = false) => {
    const form = new FormData();
    form.append('file', file);
    if (isInternal) form.append('is_internal', 'true');
    // The browser sets the multipart boundary, so the default JSON
    // content type must be cleared.
    return api
      .post(`/complaints/${complaintId}/attachments`, form, {
        headers: { 'Content-Type': undefined },
      })
      .then(unwrap);
  },
  remove: (complaintId, attachmentId) =>
    api.delete(`/complaints/${complaintId}/attachments/${attachmentId}`).then(unwrap),

  /**
   * Fetches a preview as an object URL.
   *
   * The endpoint is authorised, so the image cannot be pointed at with a
   * plain src attribute and has to be fetched with the token attached.
   */
  preview: async (complaintId, attachmentId) => {
    const response = await api.get(
      `/complaints/${complaintId}/attachments/${attachmentId}/preview`,
      { responseType: 'blob' },
    );
    return URL.createObjectURL(response.data);
  },
  /**
   * Fetches the file with the auth header and hands the browser a blob.
   *
   * A plain link cannot carry the bearer token, and the endpoint is
   * authorised, so the request is made here and saved from memory.
   */
  download: async (complaintId, attachmentId, filename) => {
    const response = await api.get(
      `/complaints/${complaintId}/attachments/${attachmentId}`,
      { responseType: 'blob' },
    );
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'attachment';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

export const dashboardService = {
  overview: () => api.get('/dashboard/overview').then(unwrap),
  studentStats: () => api.get('/dashboard/student-stats').then(unwrap),
  statusChart: () => api.get('/dashboard/charts/status').then(unwrap),
  categoryChart: () => api.get('/dashboard/charts/category').then(unwrap),
  priorityChart: () => api.get('/dashboard/charts/priority').then(unwrap),
  trendChart: (days = 30) => api.get('/dashboard/charts/trend', { params: { days } }).then(unwrap),
  monthlyChart: () => api.get('/dashboard/charts/monthly').then(unwrap),
  summary: () => api.get('/dashboard/reports/summary').then(unwrap),
  staffPerformance: () => api.get('/dashboard/reports/staff-performance').then(unwrap),

  /** Downloads a register as a spreadsheet file. */
  exportCsv: async (kind, params = {}) => {
    const response = await api.get(`/dashboard/export/${kind}`, {
      params,
      responseType: 'blob',
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${kind}-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

export const notificationService = {
  list: (params) => api.get('/notifications', { params }).then(unwrap),
  unreadCount: () => api.get('/notifications/unread-count').then(unwrap),
  markRead: (id) => api.put(`/notifications/${id}/read`).then(unwrap),
  markAllRead: () => api.put('/notifications/read-all').then(unwrap),
};

export const adminService = {
  users: (params) => api.get('/admin/users', { params }).then(unwrap),
  user: (id) => api.get(`/admin/users/${id}`).then(unwrap),
  createStaff: (data) => api.post('/admin/staff', data).then(unwrap),
  toggleActive: (id) => api.put(`/admin/users/${id}/toggle-active`).then(unwrap),
  setRole: (id, role) => api.put(`/admin/users/${id}/role`, { role }).then(unwrap),
  departments: () => api.get('/admin/departments').then(unwrap),
  createDepartment: (data) => api.post('/admin/departments', data).then(unwrap),
  updateDepartment: (id, data) => api.put(`/admin/departments/${id}`, data).then(unwrap),
  settings: () => api.get('/admin/settings').then(unwrap),
  updateSettings: (data) => api.put('/admin/settings', data).then(unwrap),
};

export const platformService = {
  institutions: () => api.get('/platform/institutions').then(unwrap),
  createInstitution: (data) => api.post('/platform/institutions', data).then(unwrap),
  toggleInstitution: (id) => api.put(`/platform/institutions/${id}/toggle-active`).then(unwrap),
  stats: () => api.get('/platform/stats').then(unwrap),
};

export default api;
