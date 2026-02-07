import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const api = axios.create({ baseURL: `${API_URL}/api` });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// Auth
export const login = (data) => api.post('/auth/login', data);
export const getMe = () => api.get('/auth/me');

// Users
export const listUsers = (params) => api.get('/users', { params });
export const createUser = (data) => api.post('/users', data);
export const updateUser = (id, data) => api.put(`/users/${id}`, data);
export const deleteUser = (id) => api.delete(`/users/${id}`);
export const listApprovers = (params) => api.get('/users/approvers', { params });
export const changePassword = (id, data) => api.put(`/users/${id}/password`, data);

// Departments
export const listDepartments = () => api.get('/departments');
export const listAllDepartments = () => api.get('/departments/all');
export const createDepartment = (data) => api.post('/departments', data);
export const updateDepartment = (id, data) => api.put(`/departments/${id}`, data);

// Form Templates
export const listTemplates = (params) => api.get('/form-templates', { params });
export const listAllTemplates = () => api.get('/form-templates/all');
export const getTemplate = (id) => api.get(`/form-templates/${id}`);
export const createTemplate = (data) => api.post('/form-templates', data);
export const updateTemplate = (id, data) => api.put(`/form-templates/${id}`, data);
export const deleteTemplate = (id) => api.delete(`/form-templates/${id}`);

// Requests
export const listRequests = (params) => api.get('/requests', { params });
export const getRequest = (id) => api.get(`/requests/${id}`);
export const createRequest = (data) => api.post('/requests', data);
export const actionRequest = (id, data) => api.post(`/requests/${id}/action`, data);

// Notifications
export const listNotifications = (params) => api.get('/notifications', { params });
export const markNotificationRead = (id) => api.post(`/notifications/${id}/read`);
export const markAllNotificationsRead = () => api.post('/notifications/read-all');

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats');

export default api;
