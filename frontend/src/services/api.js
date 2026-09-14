import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 - Token expired
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
            headers: {
              Authorization: `Bearer ${refreshToken}`,
            },
          });

          const { access_token } = response.data.data;
          localStorage.setItem('access_token', access_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;

// ==================== AUTH SERVICES ====================

export const authService = {
  register: async (data) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  login: async (data) => {
    const response = await api.post('/auth/login', data);
    return response.data;
  },

  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  updateProfile: async (data) => {
    const response = await api.put('/auth/profile', data);
    return response.data;
  },

  changePassword: async (data) => {
    const response = await api.post('/auth/change-password', data);
    return response.data;
  },

  registerAdmin: async (data) => {
    const response = await api.post('/auth/register-admin', data);
    return response.data;
  },
};

// ==================== STUDENT SERVICES ====================

export const studentService = {
  getCategories: async () => {
    const response = await api.get('/student/categories');
    return response.data;
  },

  getPriorities: async () => {
    const response = await api.get('/student/priorities');
    return response.data;
  },

  getMyComplaints: async (params = {}) => {
    const response = await api.get('/student/complaints', { params });
    return response.data;
  },

  createComplaint: async (data) => {
    const response = await api.post('/student/complaints', data);
    return response.data;
  },

  getComplaintDetails: async (id) => {
    const response = await api.get(`/student/complaints/${id}`);
    return response.data;
  },

  addResponse: async (complaintId, data) => {
    const response = await api.post(`/student/complaints/${complaintId}/responses`, data);
    return response.data;
  },

  trackComplaint: async (ticketNumber) => {
    const response = await api.get(`/student/complaints/${ticketNumber}/track`);
    return response.data;
  },

  getStats: async () => {
    const response = await api.get('/student/stats');
    return response.data;
  },

  getNotifications: async (params = {}) => {
    const response = await api.get('/student/notifications', { params });
    return response.data;
  },

  markNotificationRead: async (id) => {
    const response = await api.put(`/student/notifications/${id}/read`);
    return response.data;
  },

  markAllNotificationsRead: async () => {
    const response = await api.put('/student/notifications/read-all');
    return response.data;
  },
};

// ==================== ADMIN SERVICES ====================

export const adminService = {
  getAllComplaints: async (params = {}) => {
    const response = await api.get('/admin/complaints', { params });
    return response.data;
  },

  getComplaintDetails: async (id) => {
    const response = await api.get(`/admin/complaints/${id}`);
    return response.data;
  },

  updateStatus: async (id, data) => {
    const response = await api.put(`/admin/complaints/${id}/status`, data);
    return response.data;
  },

  updatePriority: async (id, data) => {
    const response = await api.put(`/admin/complaints/${id}/priority`, data);
    return response.data;
  },

  assignComplaint: async (id, data) => {
    const response = await api.put(`/admin/complaints/${id}/assign`, data);
    return response.data;
  },

  addResponse: async (complaintId, data) => {
    const response = await api.post(`/admin/complaints/${complaintId}/responses`, data);
    return response.data;
  },

  updateNotes: async (id, data) => {
    const response = await api.put(`/admin/complaints/${id}/notes`, data);
    return response.data;
  },

  getAllUsers: async (params = {}) => {
    const response = await api.get('/admin/users', { params });
    return response.data;
  },

  getUserDetails: async (id) => {
    const response = await api.get(`/admin/users/${id}`);
    return response.data;
  },

  toggleUserActive: async (id) => {
    const response = await api.put(`/admin/users/${id}/toggle-active`);
    return response.data;
  },

  getAdminList: async () => {
    const response = await api.get('/admin/admins');
    return response.data;
  },
};

// ==================== DASHBOARD SERVICES ====================

export const dashboardService = {
  getOverview: async () => {
    const response = await api.get('/dashboard/overview');
    return response.data;
  },

  getStatusChart: async () => {
    const response = await api.get('/dashboard/charts/status');
    return response.data;
  },

  getCategoryChart: async () => {
    const response = await api.get('/dashboard/charts/category');
    return response.data;
  },

  getPriorityChart: async () => {
    const response = await api.get('/dashboard/charts/priority');
    return response.data;
  },

  getTrendChart: async (days = 30) => {
    const response = await api.get('/dashboard/charts/trend', { params: { days } });
    return response.data;
  },

  getMonthlyChart: async () => {
    const response = await api.get('/dashboard/charts/monthly');
    return response.data;
  },

  getSummaryReport: async (params = {}) => {
    const response = await api.get('/dashboard/reports/summary', { params });
    return response.data;
  },

  getAdminPerformance: async () => {
    const response = await api.get('/dashboard/reports/admin-performance');
    return response.data;
  },
};