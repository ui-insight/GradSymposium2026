import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { getSelectedEvent } from '../../api/event';
import { PosterLocation } from '../../components/PosterLocation';
import type { PosterLocationFields } from '../../components/PosterLocation';
import type { Event } from '../../types';
import { actionClass, fieldClass } from '../../utils/competitionUi';

interface Proposal { Odd_Session: string; Session_I_Time: string; Session_II_Time: string }
interface Row extends PosterLocationFields {
  Project_ID: string; Project_Number: string; Project_Title: string;
  Presenter_Display_Name: string; Is_Active: boolean; Needs_Review: boolean;
}
interface Workspace {
  Event_ID: string; Event_Name: string; Configuration: Proposal | null;
  Confirmation: { By: string; At: string; Reference: string } | null;
  Proposal: Proposal | null; Context: string; Rows: Row[]; Final_Roster_Ready: boolean;
}
const empty: Proposal = { Odd_Session: '', Session_I_Time: '', Session_II_Time: '' };

export function PosterSessionsPage() {
  const [params, setParams] = useSearchParams(); const eventId = params.get('event_id');
  const [events, setEvents] = useState<Event[]>([]);
  const [data, setData] = useState<Workspace | null>(null);
  const [proposal, setProposal] = useState<Proposal>(empty);
  const [preview, setPreview] = useState<Workspace | null>(null);
  const [exceptions, setExceptions] = useState(false);
  const [reference, setReference] = useState(''); const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  useEffect(() => {
    let cancelled = false;
    setData(null); setPreview(null); setConfirmed(false); setExceptions(false); setReference(''); setError('');
    Promise.all([apiFetch<Event[]>('/events/'), getSelectedEvent(eventId)]).then(async ([list, event]) => {
      if (!event) throw new Error('No event is available.');
      const state = await apiFetch<Workspace>(`/poster-sessions/${event.Event_ID}`);
      if (!cancelled) { setEvents(list); setData(state); setProposal(state.Configuration || empty); }
    }).catch(err => { if (!cancelled) setError(String(err.message || err)); });
    return () => { cancelled = true; };
  }, [eventId]);
  function change(key: keyof Proposal, value: string) {
    setProposal({ ...proposal, [key]: value }); setPreview(null); setConfirmed(false); setExceptions(false);
  }
  async function run(apply: boolean) {
    if (!data) return;
    setBusy(true); setError('');
    try {
      const next = await apiFetch<Workspace>(`/poster-sessions/${data.Event_ID}${apply ? '' : '/preview'}`, {
        method: apply ? 'PUT' : 'POST',
        body: JSON.stringify(apply ? { ...proposal, Context: preview?.Context, Reference: reference, Organizer_Confirmed: confirmed, Unassigned_Numbers_Confirmed: exceptions } : proposal),
      });
      if (apply) { setData(next); setPreview(null); setConfirmed(false); setExceptions(false); setReference(''); }
      else setPreview(next);
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); setPreview(null); setConfirmed(false); setExceptions(false); }
    finally { setBusy(false); }
  }
  const sheet = preview || data;
  const flagged = preview?.Rows.some(row => row.Needs_Review);
  return <div className="text-[oklch(0.23_0.015_85)]">
    <div className="print:hidden">
      <h1 className="text-2xl font-bold">Poster boards and sessions</h1>
      <p className="mt-3 max-w-[70ch] text-sm leading-6">Boards match issued presentation numbers. Sessions follow the number’s odd/even suffix; withdrawals and numbering gaps never move a poster.</p>
      <label className="mt-6 block max-w-xl text-sm font-semibold">Event<select disabled={busy} className={fieldClass} value={data?.Event_ID || ''} onChange={e => setParams({ event_id: e.target.value })}>{!data && <option value="">Loading…</option>}{events.map(e => <option key={e.Event_ID} value={e.Event_ID}>{e.Event_Name}</option>)}</select></label>
      {error && <p role="alert" className="mt-4 border border-red-300 bg-red-50 p-4 text-red-900">{error}</p>}
      {data && <>
        <p className="mt-6 border border-[oklch(0.75_0.03_85)] p-4 text-sm leading-6">{data.Configuration ? `Confirmed by ${data.Confirmation?.By}: ${data.Confirmation?.Reference}` : 'Unconfigured. Waiting for Paul to confirm odd/even parity and both session times. No sessions have been assigned.'}</p>
        {data.Configuration && !data.Final_Roster_Ready && <p className="mt-3 text-sm font-semibold">The directory needs a current organizer signoff before publication. <Link className="underline" to={`/admin/roster-review?event_id=${data.Event_ID}`}>Review the updated directory</Link>.</p>}
        <form className="mt-8" onSubmit={e => { e.preventDefault(); void run(false); }}>
          <fieldset disabled={busy} className="grid max-w-3xl gap-5 sm:grid-cols-2">
            <legend className="mb-4 text-lg font-semibold">Preview the organizer’s convention</legend>
            <label className="text-sm font-semibold sm:col-span-2">Odd-numbered posters<select required className={fieldClass} value={proposal.Odd_Session} onChange={e => change('Odd_Session', e.target.value)}><option value="">Choose after organizer confirmation</option><option value="I">Odd → Session I; even → Session II</option><option value="II">Odd → Session II; even → Session I</option></select></label>
            {(['I', 'II'] as const).map(session => <label key={session} className="text-sm font-semibold">Session {session}: confirmed date and time<input required maxLength={150} className={fieldClass} value={proposal[`Session_${session}_Time`]} onChange={e => change(`Session_${session}_Time`, e.target.value)} aria-describedby="session-time-help" /></label>)}
            <p id="session-time-help" className="text-sm leading-6 text-gray-600 sm:col-span-2">Enter the organizer’s complete date, time range and time zone as attendees should see them. These labels do not schedule judging or create voting rounds.</p>
            <button className={`${actionClass} justify-self-start`}>Preview board and session list</button>
          </fieldset>
        </form>
      </>}
    </div>
    {sheet && <section className="mt-8 border-t border-[oklch(0.8_0.025_85)] pt-6">
      <h2 className="text-xl font-semibold">{sheet.Event_Name}: {preview ? 'proposed setup' : 'current setup'}</h2>
      {preview && <p className="mt-2 font-semibold">Draft preview. This mapping has not been applied.</p>}
      {!sheet.Proposal && <p className="mt-2 text-sm">Session mapping unconfigured. Board labels follow issued numbers.</p>}
      <button onClick={() => window.print()} className={`${actionClass} mt-4 print:hidden`}>Print this setup list</button>
      <p className="mt-3 text-sm">{sheet.Rows.filter(row => row.Is_Active).length} active posters. Withdrawn numbers stay reserved and are omitted from the printed setup list.</p>
      <ul className="mt-5 divide-y divide-[oklch(0.85_0.025_85)]">{sheet.Rows.map(row => <li key={row.Project_ID} className={`break-inside-avoid py-4 ${row.Is_Active ? '' : 'opacity-60 print:hidden'}`}>
        <p className="font-semibold">{row.Project_Number} · {row.Presenter_Display_Name}{!row.Is_Active && ' (withdrawn)'}</p>
        <p className="mt-1 text-sm">{row.Project_Title}</p><PosterLocation poster={row} />
        {row.Needs_Review && <p className="mt-2 font-semibold text-red-800">Unexpected number format. Organizer review required; no board or session assigned.</p>}
      </li>)}</ul>
    </section>}
    {preview && <form className="mt-8 border-t border-[oklch(0.8_0.025_85)] pt-6 print:hidden" onSubmit={e => { e.preventDefault(); void run(true); }}>
      <h2 className="text-lg font-semibold">Apply the confirmed convention</h2>
      <p className="mt-3 max-w-[70ch] text-sm leading-6">Applying this convention updates board/session displays for this event and future additions. Review and sign off the updated directory before publishing it.</p>
      {!preview.Final_Roster_Ready && <p className="mt-3 text-sm font-semibold">Complete <Link className="underline" to={`/admin/roster-review?event_id=${preview.Event_ID}`}>final roster review</Link> before applying.</p>}
      {flagged && <p role="alert" className="mt-3 font-semibold text-red-800">Unexpected poster numbers require explicit review and will remain unassigned.</p>}
      <fieldset disabled={busy} className="mt-4 space-y-4">
        <label className="block max-w-xl text-sm font-semibold">Organizer confirmation reference<input required maxLength={500} className={fieldClass} value={reference} onChange={e => setReference(e.target.value)} /></label>
        <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" required checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Paul confirmed this parity mapping and both session time labels; I reviewed the preview.</label>
        <span>{flagged && <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" required checked={exceptions} onChange={e => setExceptions(e.target.checked)} />I reviewed the flagged numbers. Leave their boards and sessions unassigned for organizer follow-up.</label>}</span>
        <button disabled={!confirmed || !preview.Final_Roster_Ready || (flagged && !exceptions)} className={actionClass}>Apply confirmed convention</button>
      </fieldset>
    </form>}
  </div>;
}
