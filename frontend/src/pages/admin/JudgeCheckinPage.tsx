import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { getSelectedEvent } from '../../api/event';
import { apiFetch } from '../../api/client';
import { actionClass, fieldClass } from '../../utils/competitionUi';
interface Invite { Invite_ID: string; Judge_ID: string; First_Name: string; Last_Name: string; Is_Active: boolean; Activated: boolean; Access_Code: string; token: string; Assignment_Count: number; Assignment_Limit: number }
export function JudgeCheckinPage() {
  const [eventId, setEventId] = useState('');
  const [eventName, setEventName] = useState('');
  const [invites, setInvites] = useState<Invite[]>([]);
  const [selected, setSelected] = useState('');
  const [limit, setLimit] = useState(12);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef<string | null>(null);
  const refresh = useCallback(async () => {
    const event = await getSelectedEvent();
    if (!event) return;
    setEventId(event.Event_ID); setEventName(event.Event_Name);
    const next = await apiFetch<Invite[]>(`/judge-checkin/admin?event_id=${event.Event_ID}`);
    setInvites(next);
    setSelected(current => next.some(i => i.Invite_ID === current) ? current : next[0]?.Invite_ID || '');
  }, []);
  useEffect(() => { refresh().catch(e => setError(e.message)); const timer = setInterval(() => refresh().catch(e => setError(e.message)), 3000); return () => clearInterval(timer); }, [refresh]);
  async function nextJudge() {
    if (!eventId || busy) return;
    setBusy(true); setError('');
    requestId.current ??= crypto.randomUUID();
    try {
      const result = await apiFetch<Invite>('/judge-checkin/admin', { method: 'POST', body: JSON.stringify({ Event_ID: eventId, Request_ID: requestId.current, Assignment_Limit: limit }) });
      requestId.current = null; await refresh(); setSelected(result.Invite_ID);
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to generate QR'); }
    finally { setBusy(false); }
  }
  const invite = invites.find(i => i.Invite_ID === selected);
  const url = invite ? `${window.location.origin}/judge/check-in#token=${encodeURIComponent(invite.token)}` : '';
  return <div>
    <div className="print:hidden"><h1 className="text-2xl font-bold">Judge check-in</h1><p className="mt-2">{eventName}</p><p className="mt-3 max-w-prose">Show one personal QR to each judge. They enter their name to activate it and receive an initial poster list. Then choose Next judge. Keep these codes private.</p>
    <label className="block mt-4 max-w-xs">Initial posters per judge<input className={fieldClass} type="number" min={1} max={200} value={limit} onChange={e => setLimit(Number(e.target.value))} /></label><p className="mt-2 text-sm max-w-prose">Up to this many posters are assigned at activation, spread across sessions where possible. Adjust for your staffing. Existing work is preserved; use Assignments to fill remaining coverage.</p>
    <div className="mt-4 flex flex-wrap gap-3"><button className={actionClass} onClick={nextJudge} disabled={busy || !eventId || !Number.isInteger(limit) || limit < 1 || limit > 200}>{busy ? 'Generating…' : invite ? 'Next judge: generate a new QR' : 'Generate first judge QR'}</button><button className={actionClass} disabled={!invite} onClick={() => window.print()}>Print this judge QR</button><Link className={actionClass} to={`/admin/assignments?event_id=${eventId}`}>Review coverage and assignments</Link></div>
    {error && <p role="alert" className="my-4 text-red-800">{error}</p>}</div>
    {invite && <section className="my-6 border-y border-gray-300 py-6 text-center break-inside-avoid" aria-label="Personal judge QR">
      <h2 className="text-2xl font-semibold">{invite.Activated ? `${invite.First_Name} ${invite.Last_Name}` : 'Scan to become a judge'}</h2>
      <p role="status" className="mt-2">{invite.Activated ? invite.Is_Active ? `Activated · ${invite.Assignment_Count} posters assigned` : 'Account disabled' : 'Not activated until a name is entered'}</p>
      <div className="mx-auto my-5 w-fit bg-white p-4"><QRCodeSVG value={url} size={250} title="Personal judge check-in QR" /></div>
      <p className="text-lg">Personal recovery code: <strong className="font-mono">{invite.Access_Code}</strong></p><p className="mt-2">Keep this QR or code to resume your judging later.</p><p className="mt-1">{window.location.origin}/judge</p>
      <a className="mt-4 inline-block underline print:hidden" href={url} target="_blank" rel="noreferrer">Open this personal check-in link</a>
    </section>}
    <section className="print:hidden"><h2 className="text-xl font-semibold">Issued and activated codes</h2><p className="mt-2 text-sm">Select any entry to show its QR again. Rescanning restores the same judge, assignments and scores. Unused invitations remain inactive.</p>
      <ul className="mt-4 divide-y divide-gray-300">{invites.map(i => <li key={i.Invite_ID} className="py-3 flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">{i.Activated ? `${i.First_Name} ${i.Last_Name}` : 'Awaiting name'}</p><p className="text-sm font-mono">{i.Access_Code} · {i.Activated ? i.Is_Active ? 'Activated' : 'Disabled' : 'Unused'} · {i.Assignment_Count} assigned</p></div><button className={actionClass} onClick={() => setSelected(i.Invite_ID)}>Show QR</button></li>)}</ul>{!invites.length && <p className="mt-4">Generate the first QR when your first judge arrives.</p>}
    </section>
  </div>;
}
