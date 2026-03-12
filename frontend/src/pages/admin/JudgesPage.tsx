import { useState, useEffect } from 'react';
import { apiFetch } from '../../api/client';
import type { Judge, Event, AccessCodeCard } from '../../types';

export function JudgesPage() {
  const [judges, setJudges] = useState<Judge[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCodes, setShowCodes] = useState(false);
  const [codes, setCodes] = useState<AccessCodeCard[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newJudge, setNewJudge] = useState({ First_Name: '', Last_Name: '', Email: '', Department: '' });

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const ev = await apiFetch<Event | null>('/events/active');
      setEvent(ev);
      if (ev) {
        const j = await apiFetch<Judge[]>(`/judges/?event_id=${ev.Event_ID}`);
        setJudges(j);
      }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!event) return;
    try {
      await apiFetch('/judges/', {
        method: 'POST',
        body: JSON.stringify({ Event_ID: event.Event_ID, ...newJudge }),
      });
      setNewJudge({ First_Name: '', Last_Name: '', Email: '', Department: '' });
      setShowAdd(false);
      loadData();
    } catch (err) { console.error(err); }
  }

  async function handleShowCodes() {
    if (!event) return;
    const c = await apiFetch<AccessCodeCard[]>(`/judges/access-codes?event_id=${event.Event_ID}`);
    setCodes(c);
    setShowCodes(true);
  }

  if (loading) return <div className="text-gray-500">Loading...</div>;

  // Print view for access codes
  if (showCodes) {
    return (
      <div>
        <div className="mb-4 flex gap-2 print:hidden">
          <button onClick={() => setShowCodes(false)} className="text-sm text-blue-600 hover:text-blue-800">Back</button>
          <button onClick={() => window.print()} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">Print Codes</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {codes.map(c => (
            <div key={c.Access_Code} className="border-2 border-gray-300 rounded-xl p-6 text-center">
              <p className="text-sm text-gray-500 mb-1">Judge Access Code</p>
              <p className="text-lg font-semibold mb-3">{c.First_Name} {c.Last_Name}</p>
              <p className="text-4xl font-mono font-bold tracking-widest text-blue-600">{c.Access_Code}</p>
              <p className="text-xs text-gray-400 mt-3">Enter this code at the scoring app</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Judges</h1>
        <div className="flex gap-2">
          <button onClick={handleShowCodes} className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">Print Codes</button>
          <button onClick={() => setShowAdd(!showAdd)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">Add Judge</button>
        </div>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="bg-white rounded-xl border border-gray-200 p-4 mb-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <input placeholder="First Name" value={newJudge.First_Name} onChange={e => setNewJudge(p => ({ ...p, First_Name: e.target.value }))} className="px-3 py-2 border border-gray-300 rounded-lg text-sm" required />
          <input placeholder="Last Name" value={newJudge.Last_Name} onChange={e => setNewJudge(p => ({ ...p, Last_Name: e.target.value }))} className="px-3 py-2 border border-gray-300 rounded-lg text-sm" required />
          <input placeholder="Email" value={newJudge.Email} onChange={e => setNewJudge(p => ({ ...p, Email: e.target.value }))} className="px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <div className="flex gap-2">
            <input placeholder="Department" value={newJudge.Department} onChange={e => setNewJudge(p => ({ ...p, Department: e.target.value }))} className="px-3 py-2 border border-gray-300 rounded-lg text-sm flex-1" />
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium">Save</button>
          </div>
        </form>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Name</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Dept</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Code</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">(Projects) Assigned</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">(Projects) Scored</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {judges.map(j => {
              const hasMissingScores = j.assignment_count > j.score_count;

              return (
                <tr key={j.Judge_ID} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{j.First_Name} {j.Last_Name}</td>
                  <td className="px-4 py-3 text-gray-500">{j.Email || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{j.Department || '—'}</td>
                  <td className="px-4 py-3 font-mono font-bold text-blue-600">{j.Access_Code}</td>
                  <td className="px-4 py-3 text-gray-500">{j.assignment_count} projects</td>
                  <td className={`px-4 py-3 ${hasMissingScores ? 'font-medium text-red-600' : 'text-gray-500'}`}>
                    {j.score_count} projects
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {judges.length === 0 && (
          <div className="text-center py-8 text-gray-400">No judges yet</div>
        )}
      </div>
    </div>
  );
}
