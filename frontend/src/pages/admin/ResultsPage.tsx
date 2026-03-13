import { useState, useEffect, useRef, useCallback } from 'react';
import { apiFetch } from '../../api/client';
import type { ProjectResult, Event } from '../../types';

interface ActivityItem {
  Judge_Name: string;
  Project_Number: string;
  Project_Title: string;
  Category: string;
  Total_Score: number;
  Scored_At: string | null;
}

export function ResultsPage() {
  const [results, setResults] = useState<ProjectResult[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const eventRef = useRef<Event | null>(null);

  const loadData = useCallback(async () => {
    try {
      const ev = eventRef.current || await apiFetch<Event | null>('/events/active');
      if (!eventRef.current && ev) {
        eventRef.current = ev;
        setEvent(ev);
      }
      if (ev) {
        const [r, a] = await Promise.all([
          apiFetch<ProjectResult[]>(`/results/?event_id=${ev.Event_ID}`),
          apiFetch<ActivityItem[]>(`/results/activity?event_id=${ev.Event_ID}&limit=8`)
            .catch(err => {
              console.error('Failed to load recent activity:', err);
              return [];
            }),
        ]);
        setResults(r);
        setActivity(a);
        setLastRefresh(new Date());
      }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

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

  function timeAgo(isoStr: string | null): string {
    if (!isoStr) return '';
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ago`;
  }

  const filtered = filter
    ? results.filter(r => r.Category === filter)
    : results;

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Results</h1>
          <span className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Live
          </span>
        </div>
        <div className="flex gap-2">
          <button onClick={loadData} className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">Refresh</button>
          <button onClick={handleExport} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700">Export Excel</button>
        </div>
      </div>

      <p className="text-xs text-gray-400 mb-4">
        Auto-refreshes every 10s &middot; Last updated {lastRefresh.toLocaleTimeString()}
      </p>

      {/* Recent activity feed */}
      {activity.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Recent Scoring Activity</h2>
          <div className="space-y-2">
            {activity.map((a, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    a.Category === 'Art' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                  }`}>{a.Project_Number}</span>
                  <span className="text-gray-700 font-medium truncate">{a.Judge_Name}</span>
                  <span className="text-gray-400 hidden sm:inline">scored</span>
                  <span className="text-gray-500 truncate hidden sm:inline">{a.Project_Title}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                  <span className="font-mono font-semibold text-gray-900">{a.Total_Score}</span>
                  <span className="text-xs text-gray-400 w-16 text-right">{timeAgo(a.Scored_At)}</span>
                </div>
              </div>
            ))}
          </div>
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
