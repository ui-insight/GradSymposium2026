import { PosterLocation } from '../../components/PosterLocation';
import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { getSelectedEvent } from '../../api/event';
import { RosterChanges } from '../../components/admin/RosterChanges';
import type { Event } from '../../types';
import type { DuplicateGroup, RosterRow, RosterWorkspace } from '../../types/rosterReview';
import { actionClass, fieldClass } from '../../utils/competitionUi';
import { downloadCsv } from '../../utils/downloadCsv';

type Run = (action: () => Promise<RosterWorkspace>, notice: string) => Promise<void>;
const target = (row: RosterRow) => ({ Project_ID: row.Project_ID, Context: row.Context });

function DuplicateComparison({ group, rows, busy, save }: {
  group: DuplicateGroup; rows: RosterRow[]; busy: boolean; save: (keep: RosterRow, withdraw: RosterRow, reason: string, talk: boolean) => Promise<void>;
}) {
  const [reason, setReason] = useState(''); const [verified, setVerified] = useState(false); const [talk, setTalk] = useState(false);
  const members = rows.filter(row => group.Project_IDs.includes(row.Project_ID));
  const keep = members.find(row => row.Project_ID === group.Later_ID);
  const older = members.find(row => row.Project_ID !== group.Later_ID);
  const talkOnly = keep?.Source?.flags?.includes('talk_only');
  const resolved = keep?.Acceptance === 'accepted' && older?.Acceptance === 'withdrawn' && older.Decision?.Superseded_By === keep.Project_ID;
  return <details className="border-b border-gray-300 py-3">
    <summary className="min-h-11 cursor-pointer py-3 font-semibold">Compare duplicate source rows {group.Source_Rows.join(' / ')}{resolved ? ' · resolved' : ''}</summary>
    <div className="grid gap-5 py-3 md:grid-cols-2">{members.map(row => <div key={row.Project_ID}>
      <h3 className="font-semibold">{row.Project_Number}: {row.Presenter_Name}</h3>
      <p className="mt-2 text-sm leading-6">{row.Project_Title}</p>
      <p className="mt-2 text-sm">Source row {row.Source?.source_row}. Timestamp as recorded: {row.Source?.submitted_at || 'Not supplied'}</p>
      <p className="mt-1 text-sm font-semibold">{row.Project_ID === group.Later_ID ? 'Later submission' : 'Earlier submission'} · {row.Acceptance}</p>
      <p className="mt-1 text-sm">{row.Assigned_Count} assignments, {row.Score_Count} historical score rows.</p>
      <details className="mt-2 text-xs"><summary className="cursor-pointer py-2">Source provenance</summary><p className="break-all">{row.Source?.source_file}, {row.Source?.source_sheet}, SHA-256 {row.Source?.source_sha256}</p></details>
    </div>)}</div>
    {!group.Complete_Source || !keep || !older ? <p className="py-3 text-sm text-amber-950">The complete pair and distinct, comparable timestamps are required. Check the source manifest before resolving.</p> : <form onSubmit={event => { event.preventDefault(); void save(keep, older, reason.trim(), talk); }}>
      <fieldset disabled={busy || resolved} className="space-y-3 pb-4">
        <p className="max-w-[75ch] text-sm leading-6">Retain {keep.Project_Number} and withdraw {older.Project_Number} under Paul’s keep-the-later-version decision. Both IDs and issued numbers remain reserved. The superseded version and its scores remain in history; its assignments are removed.</p>
        <label className="block text-sm font-semibold">Duplicate decision source / reason<input required maxLength={500} className={fieldClass} value={reason} onChange={event => setReason(event.target.value)} /></label>
        <label className="flex min-h-11 items-center gap-3 text-sm"><input required type="checkbox" checked={verified} onChange={event => setVerified(event.target.checked)} />I verified these source versions and timestamps.</label>
        {talkOnly && <label className="flex min-h-11 items-center gap-3 text-sm"><input required type="checkbox" checked={talk} onChange={event => setTalk(event.target.checked)} />The organizer confirmed poster participation for the retained talk-only request.</label>}
        <button className={actionClass} disabled={!verified || !reason.trim() || (talkOnly && !talk)}>Keep {keep.Project_Number}; withdraw {older.Project_Number}</button>
      </fieldset>
    </form>}
  </details>;
}

function Correction({ row, busy, save, cancel }: { row: RosterRow; busy: boolean; save: (body: object) => Promise<void>; cancel: () => void }) {
  const [fields, setFields] = useState({ Project_Title: row.Project_Title, Presenter_Display_Name: row.Presenter_Name, Institution: row.Institution || '', Advisor_Name: row.Advisor_Name || '', Table_Number: row.Table_Number || '' });
  const [reason, setReason] = useState('');
  return <form className="my-5 border border-gray-300 p-5" onSubmit={event => { event.preventDefault(); void save({ ...fields, Institution: fields.Institution.trim() || null, Advisor_Name: fields.Advisor_Name.trim() || null, Table_Number: fields.Table_Number.trim() || null, Context: row.Context, Reason: reason.trim() }); }}>
    <h2 className="text-xl font-semibold">Correct {row.Project_Number}</h2><p className="mt-2 text-sm">The ID and number stay fixed. Keep full co-presenter names together. Corrections return inclusion to pending and require a fresh preview/sign-off.</p>
    <fieldset disabled={busy} className="mt-4 grid gap-4 sm:grid-cols-2">{([
      ['Presenter_Display_Name', 'Full presenter name(s)', 300], ['Project_Title', 'Poster title', 500], ['Institution', 'Institution', 200], ['Advisor_Name', 'PI / lab', 200], ['Table_Number', 'Board / location', 20],
    ] as const).map(([key, label, length]) => <label key={key} className="text-sm font-semibold">{label}<input autoFocus={key === 'Presenter_Display_Name'} className={fieldClass} required={key === 'Project_Title' || key === 'Presenter_Display_Name'} maxLength={length} value={fields[key]} onChange={event => setFields({ ...fields, [key]: event.target.value })} /></label>)}
      <label className="text-sm font-semibold">Correction source / reason<input required maxLength={500} className={fieldClass} value={reason} onChange={event => setReason(event.target.value)} /></label>
      <div className="flex flex-wrap gap-3 sm:col-span-2"><button className={actionClass}>Save correction for review</button><button type="button" className={actionClass} onClick={cancel}>Cancel correction</button></div>
    </fieldset>
  </form>;
}

export function RosterReviewPage() {
  const [params, setParams] = useSearchParams(); const eventId = params.get('event_id');
  const [data, setData] = useState<RosterWorkspace | null>(null); const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [selected, setSelected] = useState<string[]>([]); const [filter, setFilter] = useState('pending'); const [search, setSearch] = useState('');
  const [action, setAction] = useState('accept'); const [reason, setReason] = useState(''); const [distinct, setDistinct] = useState(false); const [talk, setTalk] = useState(false);
  const [edit, setEdit] = useState<RosterRow | null>(null); const [preview, setPreview] = useState(false);
  const [acceptedCount, setAcceptedCount] = useState(''); const [sourceCount, setSourceCount] = useState(''); const [reference, setReference] = useState(''); const [finalChanges, setFinalChanges] = useState(false); const [previewReviewed, setPreviewReviewed] = useState(false);
  const load = useCallback(async (signal?: AbortSignal) => {
    const event = await getSelectedEvent(eventId); if (!event) throw new Error('No event is available.');
    const [next, active, demos] = await Promise.all([apiFetch<RosterWorkspace>(`/roster-review/${event.Event_ID}`, {signal}), apiFetch<Event | null>('/events/active', {signal}), apiFetch<Event[]>('/competition/rehearsals/list', {signal})]);
    if (signal?.aborted) return;
    setData(next); setSelected([]); setTalk(false); setDistinct(false); setReason(''); setEdit(null); setPreview(false); setPreviewReviewed(false); setFinalChanges(false); setAcceptedCount(''); setSourceCount(''); setReference('');
    setEvents([...(active ? [active] : []), ...demos.filter(d => d.Event_ID !== active?.Event_ID), ...(![active?.Event_ID, ...demos.map(d => d.Event_ID)].includes(event.Event_ID) ? [event] : [])]);
  }, [eventId]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(''); setNotice(''); setData(null);
    load(controller.signal).catch(err => { if (!controller.signal.aborted) setError(err.message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load]);
  const run: Run = async (request, message) => {
    setBusy(true); setError(''); setNotice('');
    try { const next = await request(); setData(next); setSelected([]); setTalk(false); setDistinct(false); setReason(''); setEdit(null); setPreview(false); setPreviewReviewed(false); setAcceptedCount(''); setSourceCount(''); setReference(''); setFinalChanges(false); setNotice(message); }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to save roster review.'); }
    finally { setBusy(false); }
  };
  if (loading) return <p role="status">Loading final roster review…</p>;
  if (!data) return <div role="alert"><p>{error}</p><button className={`${actionClass} mt-3`} onClick={() => { setLoading(true); void load().catch(err => setError(err.message)).finally(() => setLoading(false)); }}>Retry roster review</button></div>;
  const visible = data.Rows.filter(row => (!filter || row.Acceptance === filter || (filter === 'changed' && row.Changed) || row.Source?.flags?.includes(filter)) && `${row.Project_Number} ${row.Presenter_Name} ${row.Project_Title} ${row.Institution || ''}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  const chosen = data.Rows.filter(row => selected.includes(row.Project_ID)); const hasTalk = chosen.some(row => row.Source?.flags?.includes('talk_only')); const hasDuplicate = chosen.some(row => row.Source?.flags?.includes('duplicate'));
  const query = `?event_id=${data.Event_ID}`;
  function selectRecords(ids: string[]) { setSelected(ids); setTalk(false); setDistinct(false); }
  return <div>
    <h1 className="text-2xl font-bold">Final roster review</h1><p className="mt-2 max-w-[75ch] text-sm leading-6">Confirm poster inclusion, reconcile source versions and review the accepted directory before publication. Acceptance is separate from judging and voting eligibility. Issued numbers never change.</p>
    <label className="my-4 block max-w-xl text-sm font-semibold">Event<select disabled={busy} className={fieldClass} value={data.Event_ID} onChange={event => { setParams({event_id:event.target.value}); setSearch(''); }}>{events.map(event => <option key={event.Event_ID} value={event.Event_ID}>{event.Event_Name}</option>)}</select></label>
    {error && <div role="alert" className="my-4 border border-red-300 bg-red-50 p-4 text-red-900">{error}<button disabled={busy} className={`${actionClass} ml-3`} onClick={() => void load().then(() => setError('')).catch(err => setError(err.message))}>Reload current roster</button></div>}
    {notice && <p role="status" className="my-4 border border-green-300 bg-green-50 p-4">{notice}</p>}
    <section className="border-y border-gray-300 py-5" aria-label="Roster reconciliation counts"><h2 className="text-xl font-semibold">{data.Event_Name}</h2><p className="mt-3 text-base leading-7"><strong>{data.Counts.Accepted} accepted</strong> · {data.Counts.Withdrawn} withdrawn · {data.Counts.Pending} pending ({data.Counts.Changed} changed)</p><p className="mt-1 text-sm">{data.Counts.Total} records = {data.Counts.Source} source candidates + {data.Counts.Additions} later/manual additions.</p><p className="mt-2 text-sm">{data.Signoff ? `${data.Signoff.Current ? 'Current' : 'Outdated'} sign-off: ${data.Signoff.Signed_By}, ${data.Signoff.Signed_At.slice(0,10)}; ${data.Signoff.Accepted_Count} accepted. ${data.Signoff.Reference}` : 'Organizer sign-off pending.'}</p>
      <details className="mt-2"><summary className="cursor-pointer py-3 text-sm font-semibold underline">Reconcile against the private source manifest</summary>{data.Sources.length ? data.Sources.map(source => <div key={`${source.SHA256}-${source.Sheet}`} className="py-2 text-sm"><p>{source.Rows.length} source rows: {source.Accepted} accepted + {source.Withdrawn} withdrawn + {source.Pending} pending.</p><p className="break-all">{source.Sheet}; SHA-256 {source.SHA256}</p></div>) : <p className="text-sm">No staged source snapshot. Check manual additions against the organizer’s final list.</p>}</details>
    </section>
    <RosterChanges key={data.Event_ID} eventId={data.Event_ID} busy={busy} setBusy={setBusy} refresh={load} />
    {data.Duplicate_Groups.length > 0 && <section className="py-5" aria-label="Duplicate comparisons"><h2 className="text-xl font-semibold">Duplicate versions</h2><p className="mt-2 text-sm">Compare source details before retaining the later submission. Superseded versions remain traceable.</p>{data.Duplicate_Groups.map(group => <DuplicateComparison key={group.Project_IDs.map(id => data.Rows.find(r => r.Project_ID === id)?.Context).join('-')} group={group} rows={data.Rows} busy={busy} save={(keep, withdraw, Reason, Talk_Only_Confirmed) => run(() => apiFetch(`/roster-review/${data.Event_ID}/duplicates`, {method:'POST',body:JSON.stringify({Keep:target(keep),Withdraw:target(withdraw),Reason,Source_Verified:true,Talk_Only_Confirmed})}), 'Later version accepted; superseded version withdrawn with provenance.')} />)}</section>}
    <div className="grid gap-4 border-t border-gray-300 py-4 sm:grid-cols-2"><label className="text-sm font-semibold">Find a submission<input className={fieldClass} type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Number, full name, title or institution" /></label><label className="text-sm font-semibold">Show inclusion decisions<select className={fieldClass} value={filter} onChange={event => setFilter(event.target.value)}><option value="pending">Pending inclusion</option><option value="">All records</option><option value="accepted">Accepted posters</option><option value="withdrawn">Withdrawn</option><option value="changed">Changed, recheck</option><option value="talk_only">Talk-only requests</option><option value="co_presenters">Co-presenters</option><option value="duplicate">Duplicate candidates</option></select></label></div>
    <label className="flex min-h-11 items-center gap-3 text-sm font-semibold"><input type="checkbox" disabled={busy || visible.length === 0} checked={visible.length > 0 && visible.every(row => selected.includes(row.Project_ID))} onChange={event => selectRecords(event.target.checked ? [...new Set([...selected,...visible.map(r => r.Project_ID)])] : selected.filter(id => !visible.some(r => r.Project_ID === id)))} />Select all {visible.length} visible records</label>
    {chosen.length > 0 && <form className="my-3 border border-amber-300 bg-amber-50 p-4" onSubmit={event => { event.preventDefault(); void run(() => apiFetch(`/roster-review/${data.Event_ID}/decisions`, {method:'POST',body:JSON.stringify({Action:action,Reason:reason.trim(),Targets:chosen.map(target),Distinct_Verified:distinct,Talk_Only_Confirmed:talk})}), 'Inclusion decisions saved. Review the accepted preview and sign off before publication.'); }}><fieldset disabled={busy} className="grid gap-3 sm:grid-cols-2">
      <label className="text-sm font-semibold">Action for {chosen.length} selected records<select className={fieldClass} value={action} onChange={event => { setAction(event.target.value); setTalk(false); setDistinct(false); }}><option value="accept">Accept into poster roster</option><option value="withdraw">Withdraw from poster roster</option><option value="reopen">Return / reinstate for review</option></select></label>
      <label className="text-sm font-semibold">Inclusion decision source / reason<input required maxLength={500} className={fieldClass} value={reason} onChange={event => setReason(event.target.value)} /></label>
      {hasTalk && action === 'accept' && <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2"><input type="checkbox" required checked={talk} onChange={event => setTalk(event.target.checked)} />The organizer confirmed poster participation for the selected talk-only requests.</label>}
      {hasDuplicate && action === 'accept' && <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2"><input type="checkbox" checked={distinct} onChange={event => setDistinct(event.target.checked)} />I verified the selected duplicate candidates are distinct presentations. Otherwise use the version comparison above.</label>}
      <p className="text-sm leading-6 sm:col-span-2">This applies only to checked records. Withdrawals remove {chosen.reduce((sum,r) => sum + r.Assigned_Count,0)} current assignments; saved scores and numbers remain. Decisions and corrections invalidate the previous final sign-off.</p>
      <button className={`${actionClass} justify-self-start`} disabled={!reason.trim() || (action === 'accept' && chosen.some(r => !r.Is_Active))}>Confirm {action === 'accept' ? 'acceptance' : action === 'withdraw' ? 'withdrawal' : 'return to review'} for {chosen.length} {chosen.length === 1 ? 'record' : 'records'}</button><button type="button" className={actionClass} onClick={() => selectRecords([])}>Clear selection</button>
    </fieldset></form>}
    {edit && <Correction key={edit.Context} row={edit} busy={busy} cancel={() => setEdit(null)} save={body => run(() => apiFetch(`/roster-review/${data.Event_ID}/${edit.Project_ID}/correction`, {method:'PATCH',body:JSON.stringify(body)}), 'Correction saved. Review inclusion again; the number and existing work are preserved.')} />}
    <p className="py-2 text-sm text-gray-600">{visible.length} of {data.Rows.length} records shown.</p>
    <ul className="divide-y divide-gray-300">{visible.map(row => <li key={row.Project_ID} className="py-5"><div className="flex items-start gap-3"><label className="inline-flex min-h-11 min-w-11 items-start justify-center pt-1"><input aria-label={`Select ${row.Project_Number}`} type="checkbox" className="mt-1" disabled={busy} checked={selected.includes(row.Project_ID)} onChange={event => selectRecords(event.target.checked ? [...selected,row.Project_ID] : selected.filter(id => id !== row.Project_ID))} /></label><div className="min-w-0 flex-1"><p className="font-mono font-semibold">{row.Project_Number} <span className="font-sans">· {row.Presenter_Name}</span></p><p className="mt-2 max-w-[75ch] text-sm leading-6">{row.Project_Title}</p><p className="mt-1 text-sm">{row.Institution || 'Institution not supplied'} · {row.Changed ? 'Changed, needs another decision' : row.Acceptance}{!row.Is_Active && row.Acceptance !== 'withdrawn' ? ' · inactive, withdrawal reason pending' : ''}</p>
      <p className="mt-2 text-sm">Judging: {row.Judging_Eligible === null ? 'pending' : row.Judging_Eligible ? 'eligible' : 'excluded'} · Voting: {row.Voting_Eligible === null ? 'pending' : row.Voting_Eligible ? 'eligible' : 'excluded'}. Inclusion does not change these choices.</p>
      {row.Source && <p className="mt-2 text-sm">Source row {row.Source.source_row}; {row.Source.submitted_at}. {row.Source.flags.includes('talk_only') && <strong>Talk-only request: confirm poster inclusion.</strong>} {row.Source.flags.includes('co_presenters') && 'Keep full co-presenter names.'}</p>}
      <button disabled={busy} className={`${actionClass} mt-3`} onClick={() => setEdit(row)}>Correct metadata for {row.Project_Number}</button>
      <details className="mt-2 text-sm"><summary className="cursor-pointer py-3 font-semibold underline">Decision history for {row.Project_Number}</summary>{row.History.length ? <ol className="space-y-3">{[...row.History].reverse().map(h => <li key={h.Decision_ID}>{h.Decision}: {h.Reason}<p className="text-gray-600">{h.Recorded_By}, {h.Recorded_At} UTC. {h.Superseded_By && `Superseded by ${data.Rows.find(r => r.Project_ID === h.Superseded_By)?.Project_Number || h.Superseded_By}.`}</p><p>Recorded version: {h.Snapshot.Presenter_Name}, {h.Snapshot.Project_Title}</p></li>)}</ol> : <p>No final inclusion decision recorded.</p>}</details>
    </div></div></li>)}</ul>
    {visible.length === 0 && <p className="py-5 text-sm">No records match. Change the filter or clear your search.</p>}
    <section className="mt-5 border-t border-gray-300 py-5" aria-label="Final directory preview and sign-off"><h2 className="text-xl font-semibold">Accepted directory preview and sign-off</h2><p className="mt-2 max-w-[75ch] text-sm leading-6">This private preview includes only currently accepted posters and the fields attendees will see. The public dev draft preview may still show unconfirmed candidates. Signing off does not publish.</p>
      <div className="my-3 flex flex-wrap gap-3"><button className={actionClass} onClick={() => { setPreview(!preview); if (preview) setPreviewReviewed(false); }}> {preview ? 'Close accepted preview' : `Review ${data.Preview.posters.length} accepted posters`}</button><button className={actionClass} disabled={busy} onClick={async () => { try { const r = await apiFetch<{filename:string;content:string}>(`/roster-review/${data.Event_ID}/report`); downloadCsv(r.filename,r.content); } catch(err) { setError(err instanceof Error ? err.message : 'Unable to download report.'); } }}>Download reconciliation / operating report</button></div>
      {preview && <div className="my-4 border border-gray-300 p-4"><h3 className="text-lg font-semibold">{data.Preview.event?.Event_Name}</h3><p className="mt-2 text-sm">{data.Preview.posters.length} accepted posters; contacts, PI/lab details, source annotations and decisions are excluded.</p><ul className="mt-3 divide-y divide-gray-300">{data.Preview.posters.map(p => <li key={p.Project_Number} className="py-3"><strong className="font-mono">{p.Project_Number}</strong> · {p.Presenter_Display_Name}<p className="mt-1 text-sm">{p.Project_Title}</p><PosterLocation poster={p} /><p className="mt-1 text-sm">{p.Institution}</p></li>)}</ul></div>}
      {data.Blockers.length > 0 && <ul className="my-4 list-inside list-disc text-sm leading-7">{data.Blockers.map(b => <li key={b}>{b}</li>)}</ul>}
      <form onSubmit={event => { event.preventDefault(); void run(() => apiFetch(`/roster-review/${data.Event_ID}/signoff`, {method:'POST',body:JSON.stringify({Context:data.Context,Accepted_Count:Number(acceptedCount),Source_Count:Number(sourceCount),Reference:reference.trim(),Final_Changes_Confirmed:finalChanges,Preview_Reviewed:previewReviewed})}), 'Organizer sign-off recorded for this exact roster. Publication is still a separate step.'); }}><fieldset disabled={busy || data.Blockers.length > 0} className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">Confirmed accepted count<input required type="number" min={1} className={fieldClass} value={acceptedCount} onChange={event => setAcceptedCount(event.target.value)} /></label><label className="text-sm font-semibold">Original source count checked against manifest<input required type="number" min={0} className={fieldClass} value={sourceCount} onChange={event => setSourceCount(event.target.value)} /></label>
        <label className="text-sm font-semibold sm:col-span-2">Organizer approval reference / operating note<input required maxLength={500} className={fieldClass} value={reference} onChange={event => setReference(event.target.value)} /></label>
        <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2"><input required type="checkbox" checked={finalChanges} onChange={event => setFinalChanges(event.target.checked)} />I confirmed final additions/removals and all talk-only inclusion decisions with the organizer.</label>
        <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2"><input required disabled={!preview} type="checkbox" checked={previewReviewed} onChange={event => setPreviewReviewed(event.target.checked)} />I reviewed the accepted directory preview above.</label>
        <button className={`${actionClass} justify-self-start`} disabled={!previewReviewed || !finalChanges || Number(acceptedCount) !== data.Counts.Accepted || Number(sourceCount) !== data.Counts.Source || !reference.trim()}>Record organizer sign-off</button>
      </fieldset></form>
      <div className="mt-5 flex flex-wrap gap-4 text-sm font-semibold underline"><Link to={`/admin/projects${query}`}>Publication and eligibility controls</Link><Link to={`/admin/mentor-review${query}`}>Review mentor relationships against the final roster</Link></div>
    </section>
  </div>;
}
