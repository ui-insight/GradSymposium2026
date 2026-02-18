import { useState, useEffect } from 'react';
import { apiFetch } from '../../api/client';
import type { Rubric, Event } from '../../types';

export function RubricsPage() {
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const ev = await apiFetch<Event | null>('/events/active');
      if (ev) {
        const r = await apiFetch<Rubric[]>(`/rubrics/?event_id=${ev.Event_ID}`);
        setRubrics(r);
      }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Rubrics</h1>

      <div className="space-y-6">
        {rubrics.map(rubric => {
          // Group criteria
          const groups: Record<string, typeof rubric.criteria> = {};
          rubric.criteria.forEach(c => {
            const group = c.Criterion_Group || 'General';
            if (!groups[group]) groups[group] = [];
            groups[group].push(c);
          });

          return (
            <div key={rubric.Rubric_ID} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{rubric.Rubric_Name}</h2>
                  <p className="text-sm text-gray-500">
                    {rubric.criteria.length} criteria — Max score: {rubric.Max_Score} pts
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  rubric.Category === 'Art'
                    ? 'bg-purple-100 text-purple-700'
                    : 'bg-blue-100 text-blue-700'
                }`}>
                  {rubric.Category}
                </span>
              </div>

              <div className="p-6">
                <div className="text-xs text-gray-400 mb-3 flex justify-end gap-6">
                  <span>Poor (0)</span>
                  <span>Fair (1)</span>
                  <span>Good (2)</span>
                  <span>Excellent (3)</span>
                </div>

                {Object.entries(groups).map(([groupName, criteria]) => (
                  <div key={groupName} className="mb-4">
                    {groupName !== 'General' && (
                      <h3 className="text-sm font-semibold text-gray-700 mb-2 border-b border-gray-100 pb-1">
                        {groupName}
                      </h3>
                    )}
                    <div className="space-y-2">
                      {criteria.map(c => (
                        <div key={c.Criterion_ID} className="flex items-center justify-between py-1">
                          <span className="text-sm text-gray-700">{c.Criterion_Name}</span>
                          <span className="text-xs text-gray-400">0–{c.Max_Score}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
