import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { getSelectedEvent } from '../../api/event';
import { MentorImport } from '../../components/admin/MentorImport';
import { downloadCsv } from '../../utils/downloadCsv';
import type { Event } from '../../types';
import type { MentorDecision, MentorProject, MentorStatus, MentorWorkspace } from '../../types/mentorReview';
import { actionClass, fieldClass } from '../../utils/competitionUi';

const labels: Record<MentorStatus, string> = { unreviewed: 'Not reviewed', needs_input: 'Needs Paul’s input', stale: 'Details changed, recheck', clear: 'No conflict confirmed', conflict: 'Conflict recorded' };

function Relationship({ row, busy, onSave }: { row: MentorProject; busy: boolean; onSave: (decision: MentorDecision, note: string) => Promise<void> }) {
  const [decision, setDecision] = useState<MentorDecision | ''>(['clear', 'conflict', 'needs_input'].includes(row.Status) ? row.Status as MentorDecision : '');
  const [note, setNote] = useState(row.Note || row.Conflict_Reason || '');
  return <li className="border-b border-gray-300 py-5">
    <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1">
      <p className="font-mono font-semibold">{row.Project_Number} <span className="font-sans font-normal">· {row.Presenter_Name}</span></p>
      <p className="mt-1 max-w-[75ch] text-sm">{row.Project_Title}</p>
      <p className="mt-2 text-sm"><strong>PI / lab:</strong> {row.Advisor_Name || 'Not supplied. Confirm mentor identities with Paul.'}</p>
      {row.Institution && <p className="mt-1 text-sm text-gray-600">{row.Institution}</p>}
    </div><p className="text-sm font-semibold">{labels[row.Status]}</p></div>
    <p className="mt-2 text-sm text-gray-700">{!row.Is_Active ? 'Withdrawn, excluded from assignments.' : row.Roster_Review_Required ? 'Roster decision pending, excluded from assignments.' : row.Judging_Eligible === null ? 'Judging eligibility pending, excluded from assignments.' : !row.Judging_Eligible ? 'Ineligible for judging, excluded from assignments.' : 'Eligible for judging.'} {row.Assigned && <strong>Currently assigned to this judge.</strong>} {row.Has_Scores && 'Saved scores exist.'}</p>
    {row.Conflict_ID !== null && <div className="mt-2 border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950"><p>Recorded conflict blocks assignment and scoring. Reason: {row.Conflict_Reason}</p><p className="mt-1">Historical scores are retained and excluded while it exists.</p></div>}
    {row.Note && <p className="mt-2 whitespace-pre-wrap text-sm">{row.Note} {row.Reviewed_By && <span className="text-gray-600">({row.Reviewed_By}, {row.Reviewed_At?.slice(0, 10)})</span>}</p>}
    <details className="mt-3"><summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold underline focus-visible:outline-2">Review relationship for {row.Project_Number}</summary>
      <form className="mt-2 max-w-2xl" onSubmit={event => { event.preventDefault(); if (decision) void onSave(decision, note.trim()); }}>
        <fieldset disabled={busy} className="space-y-3">
          <label className="block text-sm font-semibold">Decision for {row.Project_Number}<select required className={fieldClass} value={decision} onChange={event => setDecision(event.target.value as MentorDecision)}><option value="">Choose a reviewed decision</option><option value="needs_input">Needs Paul’s input</option><option value="conflict">Confirmed conflict</option><option value="clear" disabled={row.Conflict_ID !== null}>No conflict confirmed</option></select></label>
          <label className="block text-sm font-semibold">Source or question for {row.Project_Number}<textarea required maxLength={500} rows={3} className={fieldClass} value={note} onChange={event => setNote(event.target.value)} placeholder="Who confirmed the relationship, or what needs clarification?" /></label>
          <p className="text-sm leading-6 text-gray-600">Check co-mentors and other supplied conflicts. A missing PI/lab or lack of a name match does not establish no conflict. Recording a conflict removes the assignment immediately.</p>
          <button className={actionClass} disabled={!decision || !note.trim()}>{busy ? 'Saving…' : `Save decision for ${row.Project_Number}`}</button>
        </fieldset>
      </form>
    </details>
  </li>;
}

export function MentorReviewPage() {
  const [params, setParams] = useSearchParams();
  const eventId = params.get('event_id'); const judgeId = params.get('judge_id');
  const [data, setData] = useState<MentorWorkspace | null>(null);
  const [events, setEvents] = useState<{ Event_ID: string; Event_Name: string }[]>([]);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [search, setSearch] = useState(''); const [filter, setFilter] = useState('pending');
  const load = useCallback(async (signal?: AbortSignal) => {
    const event = await getSelectedEvent(eventId);
    if (!event) throw new Error('No event is available.');
    const [next, active, demos] = await Promise.all([
      apiFetch<MentorWorkspace>(`/mentor-review/${event.Event_ID}${judgeId ? `?judge_id=${judgeId}` : ''}`, { signal }),
      apiFetch<Event | null>('/events/active', { signal }),
      apiFetch<Event[]>('/competition/rehearsals/list', { signal }),
    ]);
    if (signal?.aborted) return;
    setEvents([...(active ? [active] : []), ...demos.filter(d => d.Event_ID !== active?.Event_ID), ...(![active?.Event_ID, ...demos.map(d => d.Event_ID)].includes(event.Event_ID) ? [event] : [])]);
    setData(next);
  }, [eventId, judgeId]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setData(null); setError(''); setNotice('');
    load(controller.signal).catch(err => { if (!controller.signal.aborted) setError(err.message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load]);
  async function run(action: () => Promise<MentorWorkspace>, message: string) {
    setBusy(true); setError(''); setNotice('');
    try { setData(await action()); setNotice(message); }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to save review.'); }
    finally { setBusy(false); }
  }
  if (loading) return <p role="status">Loading mentor review…</p>;
  if (!data) return <div role="alert"><p>{error}</p><button className={`${actionClass} mt-3`} onClick={() => { setLoading(true); load().catch(err => setError(err.message)).finally(() => setLoading(false)); }}>Retry mentor review</button></div>;
  const selected = data.Judges.find(j => j.Judge_ID === data.Judge_ID);
  const query = `?event_id=${data.Event_ID}`;
  const visible = data.Projects.filter(row => {
    const matches = `${row.Project_Number} ${row.Presenter_Name} ${row.Project_Title} ${row.Advisor_Name || ''} ${row.Institution || ''}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase());
    return matches && (filter === 'all' || (filter === 'pending' && row.Is_Active && !['clear', 'conflict'].includes(row.Status)) || (filter === 'assigned' && row.Assigned) || (filter === 'missing' && row.Is_Active && !row.Advisor_Name?.trim()) || (filter === 'conflict' && row.Conflict_ID !== null) || row.Status === filter);
  });
  return <div>
    <h1 className="text-2xl font-bold">Mentor conflict review</h1>
    <p className="mt-2 max-w-[70ch] text-sm leading-6 text-gray-700">Review each judge against the presenters’ PI/lab information and Paul’s confirmations. Unreviewed, ambiguous and changed relationships stay unresolved. Search results never confirm identities.</p>
    <div className="my-5 grid gap-4 sm:grid-cols-2"><label className="text-sm font-semibold">Event<select disabled={busy} className={fieldClass} value={data.Event_ID} onChange={event => { setParams({ event_id: event.target.value }); setSearch(''); }}>{events.map(event => <option key={event.Event_ID} value={event.Event_ID}>{event.Event_Name}</option>)}</select></label><label className="text-sm font-semibold">Judge to review<select disabled={busy} className={fieldClass} value={data.Judge_ID || ''} onChange={event => { setParams({ event_id: data.Event_ID, judge_id: event.target.value }); setSearch(''); }}>{!data.Judge_ID && <option value="">Import or add judges first</option>}{data.Judges.map(judge => <option key={judge.Judge_ID} value={judge.Judge_ID}>{judge.Name}{judge.Is_Active ? '' : ' (inactive)'}{judge.Conflict_Review_Required ? ' · name changed' : ''}</option>)}</select></label></div>
    <details className="border-y border-gray-300 py-3"><summary className="min-h-11 cursor-pointer py-3 font-semibold">Import judge roster and mentor decisions</summary><MentorImport key={`${data.Event_ID}-judges`} eventId={data.Event_ID} judgeId={data.Judge_ID} kind="judges" onApplied={load} /><MentorImport key={`${data.Event_ID}-${data.Judge_ID}-decisions`} eventId={data.Event_ID} judgeId={data.Judge_ID} kind="decisions" onApplied={load} /></details>
    {error && <div role="alert" className="mt-4 border border-red-300 bg-red-50 p-4 text-red-900">{error}<button className={`${actionClass} ml-3`} disabled={busy} onClick={() => void load().then(() => setError('')).catch(err => setError(err.message))}>Reload review details</button></div>}
    {notice && <p role="status" className="mt-4 border border-green-300 bg-green-50 p-4 text-green-900">{notice}</p>}
    {!selected ? <p className="py-6">No active judge is available. Upload the recruited judge list above or <Link className="underline" to={`/admin/judges${query}`}>add judges</Link>.</p> : <>
      <section className="py-6" aria-label="Judge review progress"><h2 className="text-xl font-semibold">{selected.Name}</h2><p className="mt-1 text-sm text-gray-600">{selected.Department || 'Department not supplied'}</p><p className="mt-2 break-all font-mono text-xs">Judge ID: {selected.Judge_ID}</p>{selected.Previous_Name && <p className="mt-2 text-sm">Previously: {selected.Previous_Name}. Recheck earlier relationship decisions.</p>}
        <p className="mt-3 font-semibold">{data.Remaining} eligible relationships still need review.</p>
        {data.Completion_Blockers.length ? <ul className="mt-2 list-inside list-disc text-sm leading-7">{data.Completion_Blockers.map(blocker => <li key={blocker}>{blocker}</li>)}</ul> : <p className="mt-2 text-sm">All eligible relationships have a current organizer decision.</p>}
        {selected.Conflict_Review_Required && <button className={`${actionClass} mt-3`} disabled={busy || data.Completion_Blockers.length > 0} onClick={() => void run(() => apiFetch(`/mentor-review/${data.Event_ID}/${selected.Judge_ID}/complete`, { method: 'POST', body: JSON.stringify({ Context: data.Context }) }), 'Judge name correction and mentor relationships reviewed.')}>Finish review of corrected judge name</button>}
        <div className="mt-3 flex flex-wrap gap-4 text-sm font-semibold underline"><Link to={`/admin/projects${query}`}>Review roster and eligibility</Link><Link to={`/admin/assignments${query}`}>Check assignments</Link><Link to={`/admin/competition${query}`}>Manage recorded conflicts</Link></div>
      </section>
      <div className="grid gap-4 border-t border-gray-300 py-4 sm:grid-cols-2"><label className="text-sm font-semibold">Find a presenter or PI / lab<input type="search" className={fieldClass} value={search} onChange={event => setSearch(event.target.value)} placeholder="Name, lab, poster number or title" /></label><label className="text-sm font-semibold">Show relationships<select className={fieldClass} value={filter} onChange={event => setFilter(event.target.value)}><option value="pending">Active, needing review</option><option value="all">All presentations</option><option value="needs_input">Needs Paul’s input</option><option value="stale">Details changed</option><option value="conflict">Recorded conflicts</option><option value="assigned">Current assignments</option><option value="missing">Missing PI / lab</option><option value="clear">No conflict confirmed</option></select></label></div>
      <p className="py-2 text-sm text-gray-600">{visible.length} relationships shown.</p>
      {visible.length ? <ul>{visible.map(row => <Relationship key={`${row.Project_ID}-${row.Context}`} row={row} busy={busy} onSave={(Decision, Note) => run(() => apiFetch(`/mentor-review/${data.Event_ID}/${selected.Judge_ID}/${row.Project_ID}`, { method: 'PUT', body: JSON.stringify({ Decision, Note, Context: row.Context }) }), Decision === 'conflict' ? 'Conflict recorded. Any assignment was removed; historical scores remain excluded while the conflict exists.' : 'Review decision saved.')} />)}</ul> : <p className="py-6 text-sm">No relationships match. Try another filter or clear your search.</p>}
    </>}
    <section className="mt-6 border-t border-gray-300 py-6" aria-label="Assignment coverage shortages"><h2 className="text-xl font-semibold">Assignment coverage shortages</h2><p className="mt-2 text-sm leading-6">Conflicts stay in force even when there are too few judges. Return shortages to judging setup before redistributing assignments.</p>{data.Required_Reviews === null ? <p className="mt-3 text-sm">Set the required reviews in <Link className="underline" to={`/admin/competition${query}`}>Competition setup</Link> to calculate shortages.</p> : data.Assignment_Shortages.length ? <><ul className="mt-3 max-h-64 list-inside list-disc overflow-auto text-sm leading-7">{data.Assignment_Shortages.map(row => <li key={row.Project_Number}>{row.Project_Number}: {row.Assigned} assigned, {row.Target} required</li>)}</ul><button className={`${actionClass} mt-3`} onClick={() => downloadCsv('assignment-shortages.csv', 'Project_Number,Assigned,Target\r\n' + data.Assignment_Shortages.map(row => `${JSON.stringify(row.Project_Number)},${row.Assigned},${row.Target}`).join('\r\n'))}>Download shortage report</button></> : <p className="mt-3 text-sm">No assignment shortage among currently confirmed eligible presentations.</p>}</section>
  </div>;
}
