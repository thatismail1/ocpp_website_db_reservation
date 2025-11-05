import React, { createContext, useState, useContext, useEffect } from 'react';
import api from '../utils/api'; // ✅ use your axios instance with interceptors

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [userData, setUserData] = useState(null);

  // ✅ Check authentication on load
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    const storedRole = localStorage.getItem('role');
    const storedUserData = localStorage.getItem('userData');
    
    if (!token) {
      setIsAuthenticated(false);
      setRole(null);
      setUserData(null);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 8000);

    try {
      const response = await api.get('/api/auth/verify', {
        signal: controller.signal,
      });
      setIsAuthenticated(true);
      setUser(response.data.username);
      setRole(response.data.role || storedRole);
      if (storedUserData) {
        setUserData(JSON.parse(storedUserData));
      }
    } catch (error) {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      localStorage.removeItem('userData');
      setIsAuthenticated(false);
      setRole(null);
      setUserData(null);
    } finally {
      window.clearTimeout(timeoutId);
      setLoading(false);      
    }
    
  };

  // ✅ Login user and store token with role
  const login = async (username, password, loginRole = 'admin') => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 8000);    
    try {
      const response = await api.post(
        '/api/auth/login',
        {
          username,
          password,
          role: loginRole,
        },
        {
          signal: controller.signal,
        }
      ); 
      const { access_token, role: userRole, user_data } = response.data;

      if (access_token) {
        localStorage.setItem('token', access_token);
        localStorage.setItem('role', userRole);
        if (user_data) {
          localStorage.setItem('userData', JSON.stringify(user_data));
        }
        setIsAuthenticated(true);
        setUser(username);
        setRole(userRole);
        setUserData(user_data);
      }

      return { success: true, role: userRole };
    } catch (error) {
      const isAbortError =
        error.name === 'CanceledError' ||
        error.name === 'AbortError' ||
        error.code === 'ERR_CANCELED';      
      return {
        success: false,
        error: isAbortError
          ? 'Login request timed out. Please try again.'
          : error.response?.data?.detail || 'Login failed',        
      };
    } finally {
      window.clearTimeout(timeoutId);      
    }
  };

  // ✅ Logout clears token and role
  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('userData');
    setIsAuthenticated(false);
    setUser(null);
    setRole(null);
    setUserData(null);
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        loading,
        user,
        role,
        userData,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Hook to use in components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};