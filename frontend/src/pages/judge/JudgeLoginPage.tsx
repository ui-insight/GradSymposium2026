import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../components/auth/AuthContext';

export function JudgeLoginPage() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch<{ access_token: string }>('/judge/login', {
        method: 'POST',
        body: JSON.stringify({ access_code: code }),
      });
      login(data.access_token, 'judge');
      navigate('/judge/projects');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">GPSA Graduate Student</h1>
          <h2 className="text-2xl font-bold text-blue-600">Symposium 2026</h2>
          <p className="text-sm text-gray-500 mt-2">Judge Scoring Portal</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <p className="text-sm text-gray-600 mb-4">Enter your judge access code</p>

          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-2 rounded-lg mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              value={code}
              onChange={e => setCode(e.target.value.toUpperCase())}
              placeholder="ABC123"
              maxLength={6}
              className="w-full text-center text-3xl font-mono font-bold tracking-[0.3em] px-4 py-4 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none uppercase"
              autoFocus
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={loading || code.length < 6}
              className="w-full bg-blue-600 text-white py-3 rounded-xl text-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Verifying...' : 'Start Scoring'}
            </button>
          </form>
        </div>

        <p className="text-xs text-gray-400 mt-6">
          March 13, 2026 — Bruce Pitman Center
        </p>
      </div>
    </div>
  );
}
