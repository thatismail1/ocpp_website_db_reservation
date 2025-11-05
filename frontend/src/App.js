import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Chargers from './pages/Chargers';
import Users from './pages/Users';
import Logs from './pages/Logs';
import Settings from './pages/Settings';
import UserDashboard from './pages/UserDashboard';
import Layout from './components/Layout';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from './components/ui/sonner';
import './App.css';

function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthenticated, role, loading } = useAuth();
  
  // Wait for auth check to complete
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (adminOnly && role !== 'admin') {
    return <Navigate to="/user-dashboard" replace />;
  }
  
  return children;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          {/* User Dashboard Route */}
          <Route path="/user-dashboard" element={
            <ProtectedRoute>
              <UserDashboard />
            </ProtectedRoute>
          } />
          
          {/* Admin Routes */}
          <Route path="/" element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/chargers" element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Chargers />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/users" element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Users />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/logs" element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Logs />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/settings" element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Settings />
              </Layout>
            </ProtectedRoute>
          } />
        </Routes>
        <Toaster />
      </Router>
    </AuthProvider>
  );
}

export default App;