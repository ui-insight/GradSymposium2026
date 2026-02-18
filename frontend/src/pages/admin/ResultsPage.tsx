import { useState, useEffect } from 'react';
import { apiFetch } from '../../api/client';
import type { ProjectResult, Event } from '../../types';

export function ResultsPage() {
  const [results, setResults] = useState<ProjectResult[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');

  useEffect(() => { loadData(); }, []);

  useEffect(() => {
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      const ev = await apiFetch<Event | null>('/events/active');
      setEvent(ev);
      if (ev) {
        const r = await apiFetch<ProjectResult[]>(`/results/?event_id=${ev.Event_ID}`);
        setResults(r);
      }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }

  async function handleExport() {
    if (!event) return;
    const token = localStorage.getItem('access_token');
    const res = await fetch(`/api/v1/results/export?event_id=${event.Event_ID}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'symposium_results.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  }

  const filtered = filter
    ? results.filter(r => r.Category === filter)
    : results;

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Results</h1>
        <div className="flex gap-2">
          <button onClick={loadData} className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">Refresh</button>
          <button onClick={handleExport} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700">Export Excel</button>
        </div>
      </div>

      <p className="text-xs text-gray-400 mb-4">Auto-refreshes every 30 seconds</p>

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
            {f || 'All'}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Rank</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">#</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Title</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Presenter</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Dept</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Type</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">Judges</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">Total</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">Avg</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map(r => (
              <tr key={r.Project_ID} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                    r.Rank <= 3 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {r.Rank}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono">{r.Project_Number}</td>
                <td className="px-4 py-3 max-w-xs truncate">{r.Project_Title}</td>
                <td className="px-4 py-3">{r.Presenter_First_Name} {r.Presenter_Last_Name}</td>
                <td className="px-4 py-3 text-gray-500">{r.Department || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    r.Category === 'Art' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                  }`}>{r.Category}</span>
                </td>
                <td className="px-4 py-3 text-right">{r.Judge_Count}</td>
                <td className="px-4 py-3 text-right font-semibold">{r.Total_Score}</td>
                <td className="px-4 py-3 text-right font-semibold text-blue-600">{r.Average_Score}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-8 text-gray-400">No scores yet</div>
        )}
      </div>
    </div>
  );
}
