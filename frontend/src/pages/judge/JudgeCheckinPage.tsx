import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../components/auth/useAuth';
import { errorMessage } from '../../api/client';
import { actionClass, fieldClass } from '../../utils/competitionUi';
interface Claim { activated: boolean; name_confirmed?: boolean; access_token?: string; Judge_ID?: string; First_Name?: string; Last_Name?: string }
async function checkin(path: string, body: object): Promise<Claim> {
  const response = await fetch(`/api/v1/judge-checkin/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(errorMessage(data.detail, 'Unable to use this judge QR'));
  return data;
}
export function JudgeCheckinPage() {
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token') || '');
  const [first, setFirst] = useState('');
  const [last, setLast] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { login, updateUser } = useAuth();
  const navigate = useNavigate();
  function finish(data: Claim) {
    if (!data.activated || !data.access_token || !data.Judge_ID) return;
    login(data.access_token, 'judge'); updateUser({ id: data.Judge_ID, name: `${data.First_Name} ${data.Last_Name}` });
    navigate(data.name_confirmed === false ? '/judge/profile' : '/judge/projects', { replace: true });
  }
  useEffect(() => {
    let cancelled = false;
    checkin('inspect', { token }).then(data => { if (!cancelled) finish(data); }).catch(e => { if (!cancelled) setError(e.message); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // The personal link is inspected once; later name entry is an explicit action.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);
  return <main className="mx-auto min-h-screen max-w-lg px-5 py-10 bg-[#faf8f2] text-gray-900"><img src="/uidaho-logo-horizontal.png" alt="University of Idaho" className="h-10 w-auto" /><h1 className="mt-8 text-3xl font-semibold">Judge check-in</h1><p className="mt-4 leading-7">Enter your name to activate your personal judge code and see your posters. Keep your QR or recovery code to return later.</p>
    {loading ? <p className="mt-6" role="status">Checking your personal QR…</p> : <form className="mt-6 space-y-4" onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { finish(await checkin('activate', { token, First_Name: first, Last_Name: last })); } catch (e) { setError(e instanceof Error ? e.message : 'Unable to activate'); } finally { setBusy(false); } }}>
      <label className="block">First name<input className={fieldClass} autoComplete="given-name" required maxLength={100} value={first} onChange={e => setFirst(e.target.value)} /></label><label className="block">Last name<input className={fieldClass} autoComplete="family-name" required maxLength={100} value={last} onChange={e => setLast(e.target.value)} /></label><button className={`${actionClass} w-full`} disabled={busy || !token || !first.trim() || !last.trim()}>{busy ? 'Activating…' : 'Activate and see my posters'}</button>
    </form>}{error && <p role="alert" className="mt-5 text-red-800">{error}</p>}<a href="/judge" className="mt-6 inline-block underline">Use my recovery code instead</a>
  </main>;
}
