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
    <div className="min-h-screen bg-[linear-gradient(180deg,_#0f0f0f_0%,_#1b1710_100%)] px-4 py-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-5xl items-center justify-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1fr_420px]">
          <section className="rounded-[2rem] border border-[#3c3320] bg-[linear-gradient(135deg,_rgba(241,179,0,0.16),_transparent_28%),linear-gradient(180deg,_#171717_0%,_#0f0f0f_100%)] p-8 text-white shadow-2xl sm:p-10">
            <div className="inline-flex rounded-2xl bg-white px-4 py-3 shadow-sm">
              <img
                src="/uidaho-logo-horizontal.png"
                alt="University of Idaho"
                className="h-10 w-auto sm:h-12"
              />
            </div>
            <p className="mt-8 text-xs font-semibold uppercase tracking-[0.24em] text-[#f5d36e]">
              Judge Scoring Portal
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight">
              Score presentations with a fast, on-floor workflow.
            </h1>
            <p className="mt-4 max-w-lg text-base leading-7 text-[#d8ccb8]">
              Enter your six-character access code to review assigned projects,
              score each criterion and submit feedback for presenters.
            </p>
          </section>

          <div className="w-full text-center">
            <div className="rounded-[2rem] border border-[#d8c8a8] bg-white/95 p-8 shadow-2xl">
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
                  className="w-full rounded-[1.25rem] border-2 border-gray-300 bg-[#fffdf7] px-4 py-4 text-center text-3xl font-mono font-bold uppercase tracking-[0.3em] outline-none"
              autoFocus
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={loading || code.length < 6}
                  className="w-full rounded-xl bg-blue-600 py-3 text-lg font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Start Scoring'}
            </button>
          </form>
            </div>

            <p className="mt-6 text-xs text-[#d4c9b6]">
              March 13, 2026 — Bruce Pitman Center
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
