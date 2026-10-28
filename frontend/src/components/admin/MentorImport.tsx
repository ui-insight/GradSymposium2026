import { useState } from 'react';
import { apiFetch } from '../../api/client';
import type { MentorImportPreview } from '../../types/mentorReview';
import { actionClass, fieldClass } from '../../utils/competitionUi';
import { downloadCsv } from '../../utils/downloadCsv';

export function MentorImport({ eventId, judgeId, kind, onApplied }: {
  eventId: string; judgeId: string | null; kind: 'judges' | 'decisions'; onApplied: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<MentorImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const title = kind === 'judges' ? 'Upload recruited judges' : 'Upload mentor decisions';
  async function upload(apply: boolean) {
    if (!file) return;
    setBusy(true); setError('');
    try {
      const body = new FormData(); body.append('file', file);
      if (apply && preview) body.append('context', preview.Context);
      const result = await apiFetch<MentorImportPreview>(`/mentor-review/${eventId}/imports/${kind}?dry_run=${!apply}`, { method: 'POST', body });
      setPreview(result);
      if (result.Applied) await onApplied();
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to import CSV.'); if (apply) setPreview(null); }
    finally { setBusy(false); }
  }
  return <section className="border-t border-gray-300 py-5" aria-label={title}>
    <h3 className="text-lg font-semibold">{title}</h3>
    <p className="mt-2 max-w-[70ch] text-sm leading-6 text-gray-700">{kind === 'judges'
      ? 'Start with the judge template. Leave Judge_ID empty for a new judge; use an existing ID to update that account. Possible name or email duplicates need an explicit ID. Existing codes and saved work are retained. Omitted contact columns keep their values; blank cells in supplied columns clear them.'
      : 'Download a decision sheet for the selected judge after importing the roster. Check PI/lab identities, co-mentors and other conflicts with Paul. Fill Decision with conflict, clear or needs_input, and add a short source/reason in Note. Blank decisions are skipped. Changed review details require a fresh sheet.'}</p>
    <fieldset disabled={busy} className="mt-3 flex flex-wrap items-end gap-3">
      <button type="button" className={actionClass} disabled={kind === 'decisions' && !judgeId} onClick={async () => {
        setError('');
        try {
          const template = await apiFetch<{ filename: string; content: string }>(`/mentor-review/${eventId}/template/${kind}${judgeId ? `?judge_id=${judgeId}` : ''}`);
          downloadCsv(template.filename, template.content);
        } catch (err) { setError(err instanceof Error ? err.message : 'Unable to download template.'); }
      }}>{kind === 'judges' ? 'Download judge template' : 'Download selected judge’s decision sheet'}</button>
      <label className="min-w-0 flex-1 text-sm font-semibold">{kind === 'judges' ? 'Judge roster CSV' : 'Mentor decisions CSV'}
        <input type="file" accept=".csv,text/csv" className={fieldClass} onChange={event => { setFile(event.target.files?.[0] || null); setPreview(null); setError(''); }} />
      </label>
      <button type="button" className={actionClass} disabled={!file} onClick={() => void upload(false)}>{busy ? 'Checking upload…' : 'Preview upload'}</button>
    </fieldset>
    {error && <p role="alert" className="mt-3 text-red-800">{error}</p>}
    {preview && <div className="mt-4">
      <p role="status" className="font-semibold">{preview.Applied ? 'Upload applied.' : `${preview.Rows.length} valid rows. Nothing has been applied yet.`}</p>
      {preview.Errors.length > 0 && <div role="alert" className="mt-3 border border-red-300 bg-red-50 p-3 text-sm text-red-900"><p className="font-semibold">Resolve these errors and preview again. No rows will be applied while errors remain.</p><ul className="mt-2 list-inside list-disc">{preview.Errors.map(error => <li key={error}>{error}</li>)}</ul></div>}
      <div className="mt-3 max-h-80 overflow-auto"><table className="w-full text-left text-sm"><caption className="sr-only">CSV import preview</caption><thead><tr><th className="p-2">Row</th><th className="p-2">Judge</th><th className="p-2">Change</th></tr></thead><tbody>{preview.Rows.map(row => <tr key={row.Row} className="border-t border-gray-200"><td className="p-2">{row.Row}</td><td className="p-2">{row.Judge_Name || `${row.First_Name} ${row.Last_Name}`}<p className="break-all text-xs text-gray-600">{row.Judge_ID || 'New personal judge account'}</p></td><td className="p-2">{row.Action ? `${row.Action}: ${row.Email || 'No email'} · ${row.Department || 'No department'}` : `${row.Project_Number}: ${row.Decision}`}<p>{row.Note}</p>{row.Current_Name && <p>Current name: {row.Current_Name}</p>}{row.Assignment_Removed && <p className="font-semibold">Existing assignment will be removed.</p>}{row.Historical_Scores_Excluded && <p>Historical scores retained and excluded while conflict exists.</p>}</td></tr>)}</tbody></table></div>
      {!preview.Applied && <button type="button" className={`${actionClass} mt-3`} disabled={busy || preview.Errors.length > 0 || preview.Rows.length === 0} onClick={() => void upload(true)}>Apply {preview.Rows.length} reviewed rows</button>}
    </div>}
  </section>;
}
