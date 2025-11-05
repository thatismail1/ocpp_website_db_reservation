import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: API_URL,
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect on 401 for protected endpoints
    // Don't redirect for login or verify endpoints (let components handle these)
    if (error.response?.status === 401) {
      const requestUrl = error.config?.url || '';
      
      // Don't redirect if it's a login or verify request
      if (!requestUrl.includes('/auth/login') && !requestUrl.includes('/auth/verify')) {
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        localStorage.removeItem('userData');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;