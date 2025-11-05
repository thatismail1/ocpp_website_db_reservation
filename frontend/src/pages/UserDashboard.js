import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import api from '../utils/api';
import {
  Battery,
  Zap,
  TrendingUp,
  Activity,
  Power,
  Clock,
  LogOut,
  RefreshCw
} from 'lucide-react';

const UserDashboard = () => {
  const navigate = useNavigate();
  const { logout, userData, role } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Redirect if not a user
  useEffect(() => {
    if (role && role !== 'user') {
      navigate('/');
    }
  }, [role, navigate]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/user/dashboard');
      setDashboardData(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
      console.error('Error fetching dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading && !dashboardData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl flex items-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin" />
          Loading...
        </div>
      </div>
    );
  }

  if (error && !dashboardData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <Card className="p-6 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <p className="text-red-600 dark:text-red-400">{error}</p>
          <Button onClick={handleLogout} className="mt-4">
            Back to Login
          </Button>
        </Card>
      </div>
    );
  }

  const { user_info, chargers, active_session, transaction_history } = dashboardData || {};
  const quotaPercentage = user_info?.unlimited 
    ? 100 
    : user_info?.quota_kwh 
      ? (user_info.used_kwh / user_info.quota_kwh) * 100 
      : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 border-b border-slate-700 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg">
                <Battery className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Welcome, {user_info?.full_name}</h1>
                <p className="text-sm text-slate-400">RFID: {user_info?.id_tag}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                onClick={fetchDashboardData}
                variant="outline"
                size="sm"
                className="text-white border-slate-600 hover:bg-slate-700"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              <Button
                onClick={handleLogout}
                variant="outline"
                size="sm"
                className="text-white border-slate-600 hover:bg-slate-700"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quota Information */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="p-6 bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Battery className="h-5 w-5" />
                <h3 className="font-semibold">Energy Quota</h3>
              </div>
              {user_info?.unlimited && (
                <span className="px-2 py-1 bg-white/20 rounded text-xs font-bold">UNLIMITED</span>
              )}
            </div>
            {user_info?.unlimited ? (
              <p className="text-3xl font-bold">∞</p>
            ) : (
              <>
                <p className="text-3xl font-bold">{user_info?.quota_kwh?.toFixed(1)} kWh</p>
                <p className="text-sm text-white/80 mt-1">Total Quota</p>
              </>
            )}
          </Card>

          <Card className="p-6 bg-gradient-to-br from-blue-500 to-indigo-600 text-white">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="h-5 w-5" />
              <h3 className="font-semibold">Energy Used</h3>
            </div>
            <p className="text-3xl font-bold">{user_info?.used_kwh?.toFixed(2)} kWh</p>
            <p className="text-sm text-white/80 mt-1">This Month</p>
          </Card>

          <Card className="p-6 bg-gradient-to-br from-purple-500 to-pink-600 text-white">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="h-5 w-5" />
              <h3 className="font-semibold">Remaining</h3>
            </div>
            {user_info?.unlimited ? (
              <p className="text-3xl font-bold">∞</p>
            ) : (
              <>
                <p className="text-3xl font-bold">{user_info?.remaining_kwh?.toFixed(2)} kWh</p>
                <div className="mt-3 bg-white/20 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-white h-full transition-all duration-500"
                    style={{ width: `${Math.max(0, 100 - quotaPercentage)}%` }}
                  />
                </div>
              </>
            )}
          </Card>
        </div>

        {/* Active Charging Session */}
        {active_session && (
          <Card className="p-6 mb-8 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
            <div className="flex items-center gap-3 mb-4">
              <Activity className="h-6 w-6 text-yellow-600 dark:text-yellow-400 animate-pulse" />
              <h2 className="text-xl font-bold text-yellow-900 dark:text-yellow-100">Active Charging Session</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-1">Charger</p>
                <p className="text-lg font-semibold text-yellow-900 dark:text-yellow-100">{active_session.charger_id}</p>
              </div>
              <div>
                <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-1">Started At</p>
                <p className="text-lg font-semibold text-yellow-900 dark:text-yellow-100">
                  {new Date(active_session.start_time).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-1">Transaction ID</p>
                <p className="text-lg font-semibold text-yellow-900 dark:text-yellow-100 font-mono">
                  {active_session.transaction_id}
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Charger Stations Availability */}
        <Card className="p-6 mb-8 bg-white/95 dark:bg-slate-800/95">
          <div className="flex items-center gap-3 mb-6">
            <Power className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Charger Stations</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {chargers && chargers.length > 0 ? (
              chargers.map((charger) => (
                <Card 
                  key={charger.id} 
                  className={`p-4 ${
                    charger.status === 'Charging' 
                      ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
                      : charger.status === 'Available'
                      ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                      : 'bg-slate-50 dark:bg-slate-700 border-slate-200 dark:border-slate-600'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white">{charger.name}</h3>
                      <p className="text-xs text-slate-600 dark:text-slate-400">{charger.brand}</p>
                    </div>
                    <span 
                      className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        charger.status === 'Charging' 
                          ? 'bg-green-200 text-green-800 dark:bg-green-800 dark:text-green-200' 
                          : charger.status === 'Available'
                          ? 'bg-blue-200 text-blue-800 dark:bg-blue-800 dark:text-blue-200'
                          : 'bg-slate-200 text-slate-800 dark:bg-slate-600 dark:text-slate-200'
                      }`}
                    >
                      {charger.status || 'Unknown'}
                    </span>
                  </div>
                  <div className="text-sm text-slate-600 dark:text-slate-400 space-y-1">
                    <p>Power: {charger.power || 'N/A'}</p>
                    <p>Total Energy: {charger.total_energy_delivered?.toFixed(2) || '0.00'} kWh</p>
                  </div>
                </Card>
              ))
            ) : (
              <p className="text-slate-500 dark:text-slate-400 col-span-full text-center py-8">
                No chargers available
              </p>
            )}
          </div>
        </Card>

        {/* Transaction History */}
        <Card className="p-6 bg-white/95 dark:bg-slate-800/95">
          <div className="flex items-center gap-3 mb-6">
            <Clock className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Recent Transactions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Date & Time</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Charger</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Energy (kWh)</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Power (kW)</th>
                </tr>
              </thead>
              <tbody>
                {transaction_history && transaction_history.length > 0 ? (
                  transaction_history.map((transaction, index) => (
                    <tr 
                      key={index} 
                      className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50"
                    >
                      <td className="py-3 px-4 text-sm text-slate-700 dark:text-slate-300">
                        {new Date(transaction.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-700 dark:text-slate-300">
                        {transaction.charger_name}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-700 dark:text-slate-300 text-right">
                        {typeof transaction.energy_delivered === 'number' 
                          ? transaction.energy_delivered.toFixed(2) 
                          : transaction.energy_delivered}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-700 dark:text-slate-300 text-right">
                        {typeof transaction.power === 'number' 
                          ? transaction.power.toFixed(2) 
                          : transaction.power}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="py-8 text-center text-slate-500 dark:text-slate-400">
                      No transaction history available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default UserDashboard;
