'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Test credentials
    const credentials = {
      'master@aimodels.cloud': { password: 'master123', role: 'master_admin' },
      'admin@aimodels.cloud': { password: 'admin123', role: 'admin' },
    };

    const userCreds = credentials[email as keyof typeof credentials];
    if (userCreds && password === userCreds.password) {
      // Store auth in localStorage
      localStorage.setItem('aicloud_auth', JSON.stringify({
        email,
        role: userCreds.role,
        loginTime: new Date().toISOString(),
      }));
      router.push('/dashboard');
    } else {
      setError('Invalid credentials. Use:\nmaster@aimodels.cloud / master123\nor admin@aimodels.cloud / admin123');
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-8 backdrop-blur-sm">
          <div className="text-center mb-8">
            <div className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent mb-2">
              aimodel.cloud
            </div>
            <p className="text-slate-400">Admin Login</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@aimodels.cloud"
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-blue-500 outline-none transition"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-blue-500 outline-none transition"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white font-semibold py-2 rounded-lg transition"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-800">
            <p className="text-xs text-slate-400 text-center mb-3">Test Credentials:</p>
            <div className="bg-slate-800/50 rounded-lg p-3 space-y-3">
              <div className="pb-3 border-b border-slate-700">
                <p className="text-xs font-semibold text-blue-300 mb-1">Master Admin:</p>
                <p className="text-xs text-slate-300">
                  <span className="text-slate-500">Email:</span> master@aimodels.cloud
                </p>
                <p className="text-xs text-slate-300">
                  <span className="text-slate-500">Password:</span> master123
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-300 mb-1">Admin:</p>
                <p className="text-xs text-slate-300">
                  <span className="text-slate-500">Email:</span> admin@aimodels.cloud
                </p>
                <p className="text-xs text-slate-300">
                  <span className="text-slate-500">Password:</span> admin123
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
