import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import type { Judge, Project } from '../../types';
import { actionClass, fieldClass, sectionClass } from '../../utils/competitionUi';

interface Props { eventId: string; judges: Judge[]; projects: Project[]; assignments: Map<string, number>; onSaved: () => Promise<void> }
interface Conflict { Judge_ID: string; Project_ID: string }
export function QuickConflict({ eventId, judges, projects, assignments, onSaved }: Props) {
  const [search, setSearch] = useState('');
  const [projectId, setProjectId] = useState('');
  const [outgoing, setOutgoing] = useState('');
  const [replacement, setReplacement] = useState('');
  const [reason, setReason] = useState('');
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    setConflicts([]);
    apiFetch<Conflict[]>(`/competition/${eventId}/conflicts`).then(setConflicts).catch(e => setError(e.message));
  }, [eventId]);
  const matches = projects.filter(p => p.Is_Active && `${p.Project_Number} ${p.Presenter_Display_Name || `${p.Presenter_First_Name} ${p.Presenter_Last_Name}`} ${p.Project_Title}`.toLowerCase().includes(search.toLowerCase()));
  const assigned = judges.filter(j => assignments.has(`${j.Judge_ID}:${projectId}`));
  const candidates = judges.filter(j => j.Is_Active && !assignments.has(`${j.Judge_ID}:${projectId}`) && !conflicts.some(c => c.Judge_ID === j.Judge_ID && c.Project_ID === projectId));
  async function save() {
    const assignmentId = assignments.get(`${outgoing}:${projectId}`);
    if (!assignmentId) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await apiFetch<{ assigned: number; completed_reviews: number; target: number | null }>('/assignments/report-conflict', { method: 'POST', body: JSON.stringify({ Assignment_ID: assignmentId, Judge_ID: outgoing, Project_ID: projectId, Replacement_Judge_ID: replacement || null, Reason: reason }) });
      setMessage(`Conflict recorded. ${result.assigned} assigned; ${result.completed_reviews} completed valid reviews; target ${result.target ?? 'not set'}.${!replacement ? ' No replacement assigned. Review the coverage shortage.' : ''}`);
      setOutgoing(''); setReplacement(''); setReason('');
      await onSaved();
      setConflicts(await apiFetch<Conflict[]>(`/competition/${eventId}/conflicts`));
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to record conflict.'); }
    finally { setBusy(false); }
  }
  return <section className={`${sectionClass} mb-6`} aria-labelledby="quick-conflict-title">
    <h2 id="quick-conflict-title" className="text-xl font-semibold">Reported judge conflict</h2>
    <p className="my-3 text-sm">Find the poster and replace its judge after an in-person report. Prior reviews remain in history and the conflicted review is excluded from results.</p>
    <label className="block">Find poster<input className={fieldClass} value={search} onChange={e => setSearch(e.target.value)} placeholder="Poster number, presenter or title" /></label>
    <label className="block mt-3">Poster<select className={fieldClass} value={projectId} onChange={e => { setProjectId(e.target.value); setOutgoing(''); setReplacement(''); setMessage(''); }}><option value="">Choose poster</option>{matches.map(p => <option key={p.Project_ID} value={p.Project_ID}>{p.Project_Number}: {p.Presenter_Display_Name || `${p.Presenter_First_Name} ${p.Presenter_Last_Name}`} — {p.Project_Title}</option>)}</select></label>
    {projectId && <div className="mt-3 grid gap-3 sm:grid-cols-2">
      <label>Judge reporting conflict<select className={fieldClass} value={outgoing} onChange={e => setOutgoing(e.target.value)}><option value="">Choose assigned judge</option>{assigned.map(j => <option key={j.Judge_ID} value={j.Judge_ID}>{j.First_Name} {j.Last_Name}</option>)}</select></label>
      <label>Replacement<select className={fieldClass} value={replacement} onChange={e => setReplacement(e.target.value)}><option value="">Record conflict only (leaves a shortage)</option>{candidates.map(j => <option key={j.Judge_ID} value={j.Judge_ID}>{j.First_Name} {j.Last_Name} ({Array.from(assignments.keys()).filter(k => k.startsWith(`${j.Judge_ID}:`)).length} assigned)</option>)}</select></label>
      <label className="sm:col-span-2">Reason<input className={fieldClass} maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
      <button className={actionClass} disabled={busy || !outgoing || !reason.trim()} onClick={save}>{busy ? 'Saving…' : replacement ? 'Record conflict and replace judge' : 'Record conflict without replacement'}</button>
    </div>}
    {error && <p role="alert" className="mt-3 text-red-800">{error}</p>}
    {message && <p role="status" className="mt-3">{message}</p>}
    <details className="mt-4"><summary>Advanced mentor review (optional)</summary><a className="underline" href={`/admin/mentor-review?event_id=${eventId}`}>Open detailed mentor review</a></details>
  </section>;
}
