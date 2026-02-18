import { useState, useEffect, useRef } from 'react';
import { apiFetch } from '../../api/client';
import type { Project, Event, CSVImportResult } from '../../types';

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [importResult, setImportResult] = useState<CSVImportResult | null>(null);
  const [filter, setFilter] = useState<string>('');
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const ev = await apiFetch<Event | null>('/events/active');
      setEvent(ev);
      if (ev) {
        const p = await apiFetch<Project[]>(`/projects/?event_id=${ev.Event_ID}`);
        setProjects(p);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCSVUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !event) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const result = await apiFetch<CSVImportResult>(
        `/projects/import-csv?event_id=${event.Event_ID}`,
        { method: 'POST', body: formData }
      );
      setImportResult(result);
      loadData();
    } catch (err) {
      console.error(err);
    }
    if (fileRef.current) fileRef.current.value = '';
  }

  const filtered = projects.filter(p => {
    if (!filter) return true;
    if (filter === 'Poster' || filter === 'Art') return p.Category === filter;
    return true;
  });

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            onChange={handleCSVUpload}
            className="hidden"
          />
          <button
            onClick={() => fileRef.current?.click()}
            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
          >
            Import CSV
          </button>
        </div>
      </div>

      {importResult && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 text-sm">
          <p>Imported: <strong>{importResult.imported}</strong> | Skipped: {importResult.skipped}</p>
          {importResult.errors.length > 0 && (
            <ul className="mt-2 text-red-600">
              {importResult.errors.map((err, i) => <li key={i}>{err}</li>)}
            </ul>
          )}
          <button onClick={() => setImportResult(null)} className="text-blue-600 mt-2">Dismiss</button>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2 mb-4">
        {['', 'Poster', 'Art'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f || 'All'} ({f ? projects.filter(p => p.Category === f).length : projects.length})
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">#</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Title</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Presenter</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Dept</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Type</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Table</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Scores</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map(p => (
              <tr key={p.Project_ID} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono font-medium">{p.Project_Number}</td>
                <td className="px-4 py-3 max-w-xs truncate">{p.Project_Title}</td>
                <td className="px-4 py-3">{p.Presenter_First_Name} {p.Presenter_Last_Name}</td>
                <td className="px-4 py-3 text-gray-500">{p.Department || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    p.Category === 'Art'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-blue-100 text-blue-700'
                  }`}>
                    {p.Category}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{p.Table_Number || '—'}</td>
                <td className="px-4 py-3 text-gray-500">{p.score_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-8 text-gray-400">No projects found</div>
        )}
      </div>
    </div>
  );
}
