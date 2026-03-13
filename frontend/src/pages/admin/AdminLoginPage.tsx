import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../components/auth/AuthContext';

export function AdminLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      login(data.access_token, 'admin');
      navigate('/admin/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[linear-gradient(135deg,_rgba(241,179,0,0.16),_transparent_24%),linear-gradient(180deg,_#fffdf7_0%,_#f1e8d8_100%)] px-4 py-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-5xl items-center gap-8 lg:grid-cols-[1fr_420px]">
        <section className="rounded-[2rem] border border-[#cfbe99] bg-[linear-gradient(180deg,_rgba(255,255,255,0.8)_0%,_rgba(255,248,232,0.95)_100%)] p-8 shadow-2xl sm:p-10">
          <div className="inline-flex rounded-2xl bg-white px-4 py-3 shadow-sm">
            <img
              src="/uidaho-logo-horizontal.png"
              alt="University of Idaho"
              className="h-10 w-auto sm:h-12"
            />
          </div>
          <p className="mt-8 text-xs font-semibold uppercase tracking-[0.24em] text-[#8b6200]">
            Admin Access
          </p>
          <h1 className="mt-4 text-4xl font-semibold text-gray-900">
            Event operations in one place
          </h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-gray-600">
            Monitor scoring coverage, manage judges and assignments, review raw
            submissions and resolve scoring exceptions for the symposium.
          </p>
        </section>

        <div className="w-full">
          <div className="rounded-[2rem] border border-[#d7c8a9] bg-white/95 p-8 shadow-2xl">
            <h2 className="text-2xl font-semibold text-gray-900 mb-1">Admin Login</h2>
            <p className="text-sm text-gray-500 mb-6">GPSA Symposium Management</p>

          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-2 rounded-lg mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                  className="w-full rounded-xl border border-gray-300 bg-[#fffdf7] px-3 py-2.5 outline-none"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-gray-300 bg-[#fffdf7] px-3 py-2.5 outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
                className="w-full rounded-xl bg-blue-600 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="text-xs text-gray-400 mt-6 text-center">
            Dev: admin / admin
          </p>
        </div>
      </div>
      </div>
    </div>
  );
}
