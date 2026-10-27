import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { apiFetch } from '../../api/client';
import type { Project, Event, CSVImportResult } from '../../types';

const buttonClass = 'min-h-11 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold hover:bg-gray-100 disabled:cursor-wait disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-700';

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [importResult, setImportResult] = useState<CSVImportResult | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [filter, setFilter] = useState('');
  const [reviewFilter, setReviewFilter] = useState('');
  const [search, setSearch] = useState('');
  const [confirm, setConfirm] = useState<'publish' | 'hide' | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [approving, setApproving] = useState<Project | null>(null);
  const [editing, setEditing] = useState<Project | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const approvalRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (approving) approvalRef.current?.focus();
  }, [approving]);

  const loadData = useCallback(async () => {
    const ev = await apiFetch<Event | null>('/events/active');
    setEvent(ev);
    setProjects(ev ? await apiFetch<Project[]>(`/projects/?event_id=${ev.Event_ID}`) : []);
  }, []);

  useEffect(() => {
    loadData().catch(err => setError(err.message)).finally(() => setLoading(false));
  }, [loadData]);

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(''); setMessage('');
    try { await action(); }
    catch (err) { setError(err instanceof Error ? err.message : 'The action failed. Please try again.'); }
    finally { setBusy(false); }
  }

  async function importFile(selectedFile: File, preview: boolean) {
    if (!event) return;
    const formData = new FormData();
    formData.append('file', selectedFile);
    const result = await apiFetch<CSVImportResult>(
      `/projects/import-csv?event_id=${encodeURIComponent(event.Event_ID)}&dry_run=${preview}`,
      { method: 'POST', body: formData },
    );
    setImportResult(result);
    if (!preview && result.errors.length === 0) {
      setFile(null);
      setMessage(`${result.imported} draft presentations imported. ${result.skipped} unchanged records skipped.`);
      await loadData();
    }
  }

  async function publish(published: boolean) {
    if (!event) return;
    await apiFetch('/projects/publication', {
      method: 'POST', body: JSON.stringify({ Event_ID: event.Event_ID, Is_Published: published }),
    });
    setConfirm(null);
    setMessage(published ? 'Active posters are now in the public directory.' : 'The public poster directory is hidden.');
    await loadData();
  }

  async function saveEdit() {
    if (!editing) return;
    await apiFetch(`/projects/${editing.Project_ID}`, {
      method: 'PATCH',
      body: JSON.stringify({
        Project_Title: editing.Project_Title.trim(),
        Presenter_Display_Name: (editing.Presenter_Display_Name || '').trim() || null,
        Institution: (editing.Institution || '').trim() || null,
        Table_Number: (editing.Table_Number || '').trim() || null,
      }),
    });
    setEditing(null);
    setMessage('Changes saved as a draft. Publish active posters when the correction is ready.');
    await loadData();
  }

  const activePosters = projects.filter(project => project.Category === 'Poster' && project.Is_Active);
  const reviewRequired = activePosters.filter(project => project.Roster_Review_Required).length;
  const sourceRows = projects.filter(project => project.Roster_Review);
  const flagCount = (flag: string) => projects.filter(project => project.Roster_Review?.flags.includes(flag)).length;
  const published = activePosters.filter(project => project.Is_Published).length;
  const filtered = projects.filter(project => {
    const matchesCategory = !filter || project.Category === filter;
    const matchesReview = !reviewFilter || (reviewFilter === 'required'
      ? project.Roster_Review_Required : project.Roster_Review?.flags.includes(reviewFilter));
    const text = `${project.Project_Number} ${project.Presenter_Display_Name || `${project.Presenter_First_Name} ${project.Presenter_Last_Name}`} ${project.Project_Title} ${project.Institution || ''}`.toLocaleLowerCase();
    return matchesCategory && matchesReview && text.includes(search.toLocaleLowerCase().trim());
  }).sort((a, b) => a.Project_Number.localeCompare(b.Project_Number, undefined, { numeric: true }));
  const directoryURL = `${window.location.origin}/posters`;

  if (loading) return <p role="status">Loading roster…</p>;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold text-gray-900">Projects</h1><p className="mt-1 text-sm text-gray-600">{event?.Event_Name || 'No active event'}</p></div>
        <Link to="/posters" className={buttonClass}>View public lookup</Link>
      </div>
      {error && <div role="alert" className="mb-4 rounded-lg border border-red-300 bg-red-50 p-4 text-red-800">{error}</div>}
      {message && <p role="status" className="mb-4 rounded-lg border border-gray-300 p-4">{message}</p>}

      {event && <section aria-labelledby="publication-heading" className="mb-6 rounded-xl border border-gray-300 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-[65ch]">
            <h2 id="publication-heading" className="text-lg font-semibold">Public poster directory</h2>
            <p className="mt-2 text-sm leading-6 text-gray-700">{event.Public_Poster_Lookup_Enabled ? `Directory open. ${published} of ${activePosters.length} active posters published.` : 'Directory hidden. Prepare the roster before publishing.'}</p>
            <p className="mt-1 text-sm leading-6 text-gray-600">Imports and corrections stay in draft until you publish. Issued numbers remain fixed, including after withdrawal.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button disabled={busy || activePosters.length === 0 || reviewRequired > 0} onClick={() => setConfirm('publish')} className={`${buttonClass} bg-green-600`}>Publish active posters</button>
              {event.Public_Poster_Lookup_Enabled && <button disabled={busy} onClick={() => setConfirm('hide')} className={buttonClass}>Hide directory</button>}
            </div>
          </div>
          <div className="text-center">
            <QRCodeSVG value={directoryURL} size={88} title="Public poster lookup QR code" />
            <p className="mt-2 text-xs text-gray-600">Poster lookup</p>
          </div>
        </div>
        {confirm && <div className="mt-4 border-t border-gray-200 pt-4">
          <p className="text-sm">{confirm === 'publish' ? `Publish the names, titles, institutions, numbers, and locations of all ${activePosters.length} active posters?` : 'Hide the directory from attendees? Numbers and roster records will be kept.'}</p>
          <div className="mt-3 flex gap-2"><button disabled={busy} onClick={() => run(() => publish(confirm === 'publish'))} className={`${buttonClass} bg-green-600`}>Confirm {confirm === 'publish' ? 'publication' : 'hide'}</button><button disabled={busy} onClick={() => setConfirm(null)} className={buttonClass}>Cancel</button></div>
        </div>}
      </section>}

      {sourceRows.length > 0 && <section aria-labelledby="source-review-heading" className="mb-6 rounded-xl border border-amber-300 bg-amber-50 p-5">
        <h2 id="source-review-heading" className="text-lg font-semibold">Source roster review</h2>
        <p className="mt-2 max-w-[75ch] text-sm leading-6">{sourceRows.length} source submissions loaded as drafts in spreadsheet order. Every row is retained, including possible repeats and submissions that requested talks only. These numbers identify draft candidates; they do not confirm poster acceptance.</p>
        <p className="mt-2 text-sm font-semibold">{reviewRequired} active submissions need a decision before publication. No duplicate has been merged or talk-only submission accepted automatically.</p>
        <div className="mt-4 flex flex-wrap gap-2" aria-label="Roster review filters">
          {[
            ['', `All source rows (${sourceRows.length})`],
            ['required', `Needs review (${projects.filter(project => project.Roster_Review_Required).length})`],
            ['duplicate', `Duplicate candidates (${flagCount('duplicate')})`],
            ['talk_only', `Talk-only (${flagCount('talk_only')})`],
            ['co_presenters', `Co-presenters (${flagCount('co_presenters')})`],
          ].map(([value, label]) => <button key={value} aria-pressed={reviewFilter === value} onClick={() => setReviewFilter(value)} className={`${buttonClass} ${reviewFilter === value ? 'bg-blue-100' : ''}`}>{label}</button>)}
        </div>
      </section>}

      {event && <section aria-labelledby="import-heading" className="mb-6 rounded-xl border border-gray-300 bg-white p-5">
        <h2 id="import-heading" className="text-lg font-semibold">Import a draft roster</h2>
        <p className="mt-2 max-w-[70ch] text-sm leading-6 text-gray-600">Preview a reviewed CSV before importing. Leave Project_Number blank to assign the next unused number. Repeat uploads skip unchanged records; revisions need review.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <input ref={fileRef} type="file" accept=".csv,text/csv" aria-label="Roster CSV" className="hidden" onChange={e => {
            const selected = e.target.files?.[0];
            if (selected) { setFile(selected); setImportResult(null); run(() => importFile(selected, true)); }
            e.target.value = '';
          }} />
          <button disabled={busy} onClick={() => fileRef.current?.click()} className={buttonClass}>{busy ? 'Working…' : 'Preview CSV'}</button>
          <a href="/poster-import-template.csv" download className={buttonClass}>Download CSV template</a>
        </div>
        {importResult && <div className="mt-5">
          {importResult.errors.length > 0 ? <div role="alert"><p className="font-semibold text-red-800">No records imported. Resolve these issues first:</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-red-800">{importResult.errors.map((issue, index) => <li key={index}>{issue}</li>)}</ul></div> : file ? <>
            <p className="text-sm font-semibold">Preview: {importResult.imported} new drafts, {importResult.skipped} unchanged records.</p>
            <p className="mt-1 text-sm text-gray-600">Numbers below are provisional until import completes.</p>
            {importResult.preview.length > 0 && <ul className="mt-3 max-h-72 divide-y divide-gray-200 overflow-auto border-y border-gray-200">{importResult.preview.map(project => <li key={project.Project_ID} className="py-3 text-sm"><span className="mr-3 font-mono font-semibold">{project.Project_Number}</span>{project.Presenter_Display_Name || `${project.Presenter_First_Name} ${project.Presenter_Last_Name}`}<p className="mt-1 text-gray-600">{project.Project_Title}</p></li>)}</ul>}
            <div className="mt-4 flex gap-2"><button disabled={busy || importResult.imported === 0} onClick={() => run(() => importFile(file, false))} className={`${buttonClass} bg-green-600`}>Import {importResult.imported} drafts</button><button disabled={busy} onClick={() => { setFile(null); setImportResult(null); }} className={buttonClass}>Cancel</button></div>
          </> : null}
        </div>}
      </section>}

      {editing && <form className="mb-6 space-y-4 rounded-xl border border-gray-300 bg-white p-5" onSubmit={e => { e.preventDefault(); run(saveEdit); }}>
        <h2 className="text-lg font-semibold">Edit poster {editing.Project_Number}</h2>
        <p className="text-sm text-gray-600">Saving a correction returns this poster to draft for review.</p>
        {([
          ['Presenter_Display_Name', 'Presenter name(s)', 300],
          ['Project_Title', 'Poster title', 500],
          ['Institution', 'Institution', 200],
          ['Table_Number', 'Board / table location', 20],
        ] as const).map(([field, label, maxLength]) => <label key={field} className="block text-sm font-semibold">{label}<input required={field === 'Project_Title' || field === 'Presenter_Display_Name'} maxLength={maxLength} value={editing[field] || ''} onChange={e => setEditing({ ...editing, [field]: e.target.value })} className="mt-2 min-h-11 w-full rounded-lg border border-gray-300 bg-white px-3 font-normal" /></label>)}
        <div className="flex gap-2"><button disabled={busy} className={`${buttonClass} bg-green-600`}>Save draft</button><button type="button" disabled={busy} onClick={() => setEditing(null)} className={buttonClass}>Cancel</button></div>
      </form>}

      {approving && <section ref={approvalRef} tabIndex={-1} aria-labelledby="approve-heading" className="mb-6 rounded-xl border border-amber-300 bg-amber-50 p-5">
        <h2 id="approve-heading" className="text-lg font-semibold">Include {approving.Project_Number} in the poster roster?</h2>
        <p className="mt-2 font-semibold">{approving.Presenter_Display_Name || `${approving.Presenter_First_Name} ${approving.Presenter_Last_Name}`}</p>
        <p className="mt-1">{approving.Project_Title}</p>
        <p className="mt-3 max-w-[70ch] text-sm leading-6">Confirm that you have checked the source flags and this submission should remain in the poster roster. Withdraw any superseded duplicate separately. This records your decision and keeps the poster in draft until publication.</p>
        <div className="mt-4 flex gap-2"><button disabled={busy} onClick={() => run(async () => {
          await apiFetch(`/projects/${approving.Project_ID}/approve-roster`, { method: 'POST' });
          setApproving(null);
          setMessage('Roster inclusion approved. The poster remains a draft until publication.');
          await loadData();
        })} className={buttonClass}>Confirm inclusion</button><button disabled={busy} onClick={() => setApproving(null)} className={buttonClass}>Cancel</button></div>
      </section>}

      <label className="mb-4 block text-sm font-semibold">Search draft roster<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Name, poster number, title, or institution" className="mt-2 min-h-11 w-full rounded-lg border border-gray-300 bg-white px-3 font-normal" /></label>
      <div className="mb-4 flex flex-wrap gap-2" aria-label="Project categories">
        {['', 'Poster', 'Art'].map(category => <button key={category} aria-pressed={filter === category} onClick={() => setFilter(category)} className={`${buttonClass} ${filter === category ? 'bg-blue-100' : ''}`}>{category || 'All'} ({category ? projects.filter(project => project.Category === category).length : projects.length})</button>)}
      </div>
      <p role="status" className="mb-3 text-sm text-gray-600">Showing {filtered.length} of {projects.length} submissions.</p>
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Numbered presentation roster and publication status</caption>
          <thead className="border-b border-gray-200 bg-gray-50"><tr>{['Number', 'Presentation', 'Institution', 'Location', 'Status', 'Source / review', 'Actions'].map(heading => <th key={heading} scope="col" className="px-4 py-3 font-semibold">{heading}</th>)}</tr></thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map(project => <tr key={project.Project_ID}>
              <td className="whitespace-nowrap px-4 py-4 align-top font-mono font-semibold">{project.Project_Number}</td>
              <td className="min-w-64 px-4 py-4 align-top"><p className="font-semibold">{project.Presenter_Display_Name || `${project.Presenter_First_Name} ${project.Presenter_Last_Name}`}</p><p className="mt-1 max-w-lg leading-6 text-gray-600">{project.Project_Title}</p></td>
              <td className="px-4 py-4 align-top">{project.Institution || project.Department || '—'}</td>
              <td className="px-4 py-4 align-top">{project.Table_Number || 'Unassigned'}</td>
              <td className="px-4 py-4 align-top">{!project.Is_Active ? 'Withdrawn' : project.Roster_Review_Required ? 'Draft: needs review' : project.Category !== 'Poster' ? 'Art' : project.Is_Published && event?.Public_Poster_Lookup_Enabled ? 'Published' : 'Draft'}</td>
              <td className="min-w-56 px-4 py-4 align-top text-xs leading-5">{project.Roster_Review ? <>
                <p className="font-semibold">Source row {project.Roster_Review.source_row}</p>
                <p>{project.Roster_Review.current_position}</p>
                {project.Roster_Review.flags.includes('duplicate') && <p className="mt-1 font-semibold text-amber-900">Possible repeat: rows {project.Roster_Review.duplicate_rows.join(', ')}</p>}
                {project.Roster_Review.flags.includes('talk_only') && <p className="mt-1 font-semibold text-amber-900">Talk-only request. Confirm poster inclusion.</p>}
                {project.Roster_Review.flags.includes('co_presenters') && <p className="mt-1">Co-presenters share this number.</p>}
                <details className="mt-2"><summary className="cursor-pointer">Source details</summary><p className="mt-1 break-words">{project.Roster_Review.source_file}, {project.Roster_Review.source_sheet}</p><p className="mt-1">Requested: {project.Roster_Review.requested_formats}</p></details>
              </> : '—'}</td>
              <td className="px-4 py-3 align-top">
                {project.Is_Active && project.Roster_Review_Required && <button disabled={busy} onClick={() => { setApproving(project); setEditing(null); }} className={`${buttonClass} mb-2`}>Approve inclusion<span className="sr-only"> {project.Project_Number}</span></button>}
                <div className="flex gap-2"><button disabled={busy} onClick={() => setEditing({ ...project, Presenter_Display_Name: project.Presenter_Display_Name || `${project.Presenter_First_Name} ${project.Presenter_Last_Name}`.trim() })} className={buttonClass}>Edit<span className="sr-only"> {project.Project_Number}</span></button>
                  {project.Is_Active ? <button disabled={busy} onClick={() => setConfirmId(project.Project_ID)} className={buttonClass}>Withdraw<span className="sr-only"> {project.Project_Number}</span></button> : <button disabled={busy} onClick={() => run(async () => { await apiFetch(`/projects/${project.Project_ID}/reinstate`, { method: 'POST' }); await loadData(); })} className={buttonClass}>Reinstate</button>}</div>
                {confirmId === project.Project_ID && <div className="mt-3"><p>Withdraw {project.Project_Number}? Its number stays reserved.</p><div className="mt-2 flex gap-2"><button disabled={busy} onClick={() => run(async () => { await apiFetch(`/projects/${project.Project_ID}/withdraw`, { method: 'POST' }); setConfirmId(null); await loadData(); })} className={buttonClass}>Confirm</button><button onClick={() => setConfirmId(null)} className={buttonClass}>Cancel</button></div></div>}
              </td>
            </tr>)}
          </tbody>
        </table>
        {filtered.length === 0 && <p className="p-6 text-sm text-gray-600">{projects.length ? 'No submissions match these filters.' : 'No presentations yet. Preview a reviewed CSV to prepare the roster.'}</p>}
      </div>
    </div>
  );
}
