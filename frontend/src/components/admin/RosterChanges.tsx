import { useState } from 'react';
import { apiFetch } from '../../api/client';
import type { RosterChangePreview } from '../../types/rosterReview';
import { actionClass, fieldClass } from '../../utils/competitionUi';
import { downloadCsv } from '../../utils/downloadCsv';

export function RosterChanges({ eventId, busy, setBusy, refresh }: {
  eventId: string; busy: boolean; setBusy: (value: boolean) => void; refresh: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [plan, setPlan] = useState<RosterChangePreview | null>(null);
  const [error, setError] = useState('');
  async function upload(apply: boolean) {
    if (!file) return;
    setBusy(true); setError('');
    try {
      const body = new FormData(); body.append('file', file);
      if (apply && plan) body.append('context', plan.Context);
      const result = await apiFetch<RosterChangePreview>(`/roster-review/${eventId}/changes-csv?dry_run=${!apply}`, { method: 'POST', body });
      setPlan(result);
      if (result.Applied) await refresh();
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to import changes.'); if (apply) setPlan(null); }
    finally { setBusy(false); }
  }
  return <details className="border-y border-gray-300 py-3">
    <summary className="min-h-11 cursor-pointer py-3 font-semibold">Upload final additions, corrections and removals</summary>
    <p className="my-3 max-w-[75ch] text-sm leading-6">Download the current change sheet. Choose add, correct, accept, withdraw or reopen in Action and supply a reason/source. Blank actions are skipped; removing a row from the sheet never withdraws it. Existing IDs, numbers and source columns stay fixed. Use the comparison below for duplicates.</p>
    <p className="mb-3 max-w-[75ch] text-sm leading-6">For add, leave ID and number empty and fill Title and the full Presenter_Display_Name. New numbers are never reused. Corrections become pending for another inclusion review. For talk-only acceptance, set Talk_Only_Confirmed to true after checking poster participation.</p>
    <fieldset disabled={busy} className="flex flex-wrap items-end gap-3">
      <button className={actionClass} type="button" onClick={async () => {
        setError('');
        try { const result = await apiFetch<{filename: string; content: string}>(`/roster-review/${eventId}/template`); downloadCsv(result.filename, result.content); }
        catch (err) { setError(err instanceof Error ? err.message : 'Unable to download change sheet.'); }
      }}>Download current change sheet</button>
      <label className="min-w-0 flex-1 text-sm font-semibold">Final changes CSV<input className={fieldClass} type="file" accept=".csv,text/csv" onChange={event => { setFile(event.target.files?.[0] || null); setPlan(null); setError(''); }} /></label>
      <button className={actionClass} type="button" disabled={!file} onClick={() => void upload(false)}>Preview final changes</button>
    </fieldset>
    {error && <p role="alert" className="mt-3 text-red-800">{error}</p>}
    {plan && <div className="my-4">
      <p role="status" className="font-semibold">{plan.Applied ? 'Final changes applied as reviewed drafts.' : `${plan.Rows.length} proposed changes. Nothing has been saved.`}</p>
      {plan.Errors.length > 0 && <div role="alert" className="mt-3 border border-red-300 bg-red-50 p-3 text-sm text-red-900"><p>No rows will be applied while errors remain.</p><ul className="list-inside list-disc">{plan.Errors.map(e => <li key={e}>{e}</li>)}</ul></div>}
      <ul className="mt-3 max-h-80 divide-y divide-gray-300 overflow-auto text-sm">{plan.Rows.map(row => <li key={row.Row} className="py-3"><strong>Row {row.Row}: {row.Action} {row.Project_Number || '(new number pending)'}</strong><p>{row.Presenter_Name}</p>{row.Action === 'correct' && <p>Proposed presenter name(s): {String(row.Payload.Presenter_Display_Name || row.Presenter_Name)}</p>}<p>{String(row.Payload.Project_Title || row.Title || '')}</p><p className="mt-1">{row.Reason}</p>{(row.Assignments_Removed || 0) > 0 && <p>{row.Assignments_Removed} assignments will be removed. Historical scores remain stored.</p>}</li>)}</ul>
      {!plan.Applied && <button className={`${actionClass} mt-3`} disabled={busy || plan.Errors.length > 0 || plan.Rows.length === 0} onClick={() => void upload(true)}>Apply {plan.Rows.length} final changes</button>}
    </div>}
  </details>;
}
