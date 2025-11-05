import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { Battery, Loader2 } from 'lucide-react';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loginType, setLoginType] = useState('admin'); // 'admin' or 'user'

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(username, password, loginType);
    
    if (result.success) {
      // Redirect based on role
      if (result.role === 'user') {
        navigate('/user-dashboard');
      } else {
        navigate('/');
      }
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }} />
      </div>

      <Card className="w-full max-w-md relative z-10 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-slate-200 dark:border-slate-700 shadow-2xl">
        <div className="p-8">
          {/* Logo and title */}
          <div className="flex flex-col items-center mb-8">
            <div className="p-4 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl mb-4 shadow-lg">
              <Battery className="h-12 w-12 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">EV CMS Portal</h1>
            <p className="text-slate-600 dark:text-slate-400 text-center">OCPP 1.6 Charging Management System</p>
          </div>

          {/* Login Type Toggle */}
          <div className="flex gap-2 mb-6 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
            <button
              type="button"
              onClick={() => {
                setLoginType('admin');
                setUsername('');
                setPassword('');
                setError('');
              }}
              className={`flex-1 py-2 px-4 rounded-md font-medium transition-all ${
                loginType === 'admin'
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Admin Login
            </button>
            <button
              type="button"
              onClick={() => {
                setLoginType('user');
                setUsername('');
                setPassword('');
                setError('');
              }}
              className={`flex-1 py-2 px-4 rounded-md font-medium transition-all ${
                loginType === 'user'
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              User Login
            </button>
          </div>

          {/* Login form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-slate-700 dark:text-slate-300">
                {loginType === 'admin' ? 'Username' : 'RFID Tag Number'}
              </Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={loginType === 'admin' ? 'Enter your username' : 'Enter your RFID tag'}
                required
                data-testid="login-username-input"
                className="h-11"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-slate-700 dark:text-slate-300">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                data-testid="login-password-input"
                className="h-11"
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg" data-testid="login-error-message">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              data-testid="login-submit-button"
              className="w-full h-11 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-medium shadow-lg"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Logging in...
                </>
              ) : (
                'Login'
              )}
            </Button>
          </form>

          {/* Demo credentials */}
          <div className="mt-6 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
            {loginType === 'admin' ? (
              <>
                <p className="text-xs text-slate-600 dark:text-slate-400 mb-2 font-medium">Admin Credentials:</p>
                <p className="text-xs text-slate-700 dark:text-slate-300">Username: <span className="font-mono font-semibold">admin</span></p>
                <p className="text-xs text-slate-700 dark:text-slate-300">Password: <span className="font-mono font-semibold">admin123</span></p>
              </>
            ) : (
              <>
                <p className="text-xs text-slate-600 dark:text-slate-400 mb-2 font-medium">User Login Info:</p>
                <p className="text-xs text-slate-700 dark:text-slate-300">Username: <span className="font-mono font-semibold">Your RFID Tag</span></p>
                <p className="text-xs text-slate-700 dark:text-slate-300">Password: <span className="font-mono font-semibold">evcharger2025</span></p>
              </>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Login;