import { useState, useEffect } from 'react';
import { apiFetch } from '../../api/client';
import { getSelectedEvent } from '../../api/event';
import type { Judge, Project, Event, Assignment } from '../../types';

export function AssignmentsPage() {
  const [judges, setJudges] = useState<Judge[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('Poster');
  const [judgesPerProject, setJudgesPerProject] = useState(3);
  const [assignmentMap, setAssignmentMap] = useState<Map<string, number>>(new Map());
  const [toggling, setToggling] = useState<Set<string>>(new Set());

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const ev = await getSelectedEvent();
      setEvent(ev);
      if (ev) {
        const [j, p, a] = await Promise.all([
          apiFetch<Judge[]>(`/judges/?event_id=${ev.Event_ID}`),
          apiFetch<Project[]>(`/projects/?event_id=${ev.Event_ID}`),
          apiFetch<Assignment[]>(`/assignments/?event_id=${ev.Event_ID}`),
        ]);
        setJudges(j.filter(judge => judge.Is_Active));
        setProjects(p);
        const map = new Map<string, number>();
        for (const assignment of a) {
          map.set(`${assignment.Judge_ID}:${assignment.Project_ID}`, assignment.Assignment_ID);
        }
        setAssignmentMap(map);
      }
    } catch (err) { setError(err instanceof Error ? err.message : 'The action failed.'); }
    finally { setLoading(false); }
  }

  async function handleToggle(judgeId: string, projectId: string) {
    const key = `${judgeId}:${projectId}`;
    if (toggling.has(key)) return;
    setToggling(prev => new Set(prev).add(key));

    try {
      const existingId = assignmentMap.get(key);
      if (existingId !== undefined) {
        await apiFetch(`/assignments/${existingId}`, { method: 'DELETE' });
        setAssignmentMap(prev => { const m = new Map(prev); m.delete(key); return m; });
      } else {
        const result = await apiFetch<Assignment>('/assignments/', {
          method: 'POST',
          body: JSON.stringify({ Judge_ID: judgeId, Project_ID: projectId }),
        });
        setAssignmentMap(prev => new Map(prev).set(key, result.Assignment_ID));
      }
    } catch (err) { setError(err instanceof Error ? err.message : 'The action failed.'); }
    finally {
      setToggling(prev => { const s = new Set(prev); s.delete(key); return s; });
    }
  }

  async function handleAutoAssign() {
    if (!event) return;

    setBusy(true); setError(''); setNotice('');
    try {
      const result = await apiFetch<{ created: number; shortages: { Project_Number: string; Assigned: number; Target: number }[] }>('/assignments/auto', { method: 'POST', body: JSON.stringify({ Event_ID: event.Event_ID, Judges_Per_Project: judgesPerProject, Category: filter || null }) });
      setNotice(`${result.created} assignments added. ${result.shortages.length ? 'Below target: ' + result.shortages.map(item => `${item.Project_Number} (${item.Target - item.Assigned} short)`).join(', ') : 'All eligible presentations meet the assignment target.'}`);
      await loadData();
    } catch (err) { setError(err instanceof Error ? err.message : 'Assignment distribution failed.'); }
    finally { setBusy(false); }
  }

  async function handleClearAll() {
    if (!event || !confirm('Remove all judge assignments? This cannot be undone.')) return;
    try {
      await apiFetch(`/assignments/clear?event_id=${event.Event_ID}`, { method: 'DELETE' });
      setAssignmentMap(new Map());
    } catch (err) { setError(err instanceof Error ? err.message : 'The action failed.'); }
  }

  const filteredProjects = projects
    .filter(p => p.Is_Active && (!filter || p.Category === filter))
    .sort((a, b) => a.Project_Number.localeCompare(b.Project_Number, undefined, { numeric: true }));

  // Compute totals
  const projectCounts = new Map<string, number>();
  const judgeTotals = new Map<string, number>();
  for (const key of assignmentMap.keys()) {
    const [jid, pid] = key.split(':');
    projectCounts.set(pid, (projectCounts.get(pid) || 0) + 1);
    judgeTotals.set(jid, (judgeTotals.get(jid) || 0) + 1);
  }

  const totalAssignments = assignmentMap.size;
  const avgPerJudge = judges.length ? (totalAssignments / judges.length).toFixed(1) : '0';
  const avgPerProject = projects.length ? (totalAssignments / projects.length).toFixed(1) : '0';

  const posterCount = projects.filter(p => p.Category === 'Poster').length;
  const artCount = projects.filter(p => p.Category === 'Art').length;

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      {error && <p role="alert" className="mb-4 border border-red-300 bg-red-50 p-4 text-red-800">{error}</p>}
      {notice && <p role="status" className="mb-4 border border-gray-300 p-4">{notice}</p>}
      <p className="mb-4 text-sm leading-6">{event?.Event_Name}. Automatic distribution preserves existing assignments, skips pending or excluded presentations, and enforces recorded conflicts. Assignment counts are separate from completed reviews in Competition setup.</p>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assignments</h1>
          <p className="text-sm text-gray-500 mt-1">
            {totalAssignments} total &middot; {avgPerJudge} avg/judge &middot; {avgPerProject} avg/project
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 bg-white rounded-xl border border-gray-200 p-4 mb-4 flex-wrap">
        <span className="text-sm font-medium text-gray-700">Auto-assign</span>
        <input
          type="number"
          min={1}
          max={100}
          value={judgesPerProject}
          onChange={e => setJudgesPerProject(Number(e.target.value))}
          className="w-16 px-2 py-1.5 border border-gray-300 rounded-lg text-sm text-center"
        />
        <span className="text-sm text-gray-500">judges per {filter || 'all'} project</span>
        <button
          onClick={handleAutoAssign}
          disabled={busy || judges.length === 0 || !Number.isInteger(judgesPerProject) || judgesPerProject < 1}
          className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          Distribute
        </button>
        <div className="ml-auto">
          <button
            onClick={handleClearAll}
            className="bg-red-50 text-red-600 px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-red-100 border border-red-200"
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Category tabs */}
      <div className="flex gap-2 mb-4">
        {[
          { key: 'Poster', label: `Poster (${posterCount})` },
          { key: 'Art', label: `Art (${artCount})` },
          { key: '', label: `All (${projects.length})` },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filter === tab.key
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Matrix */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="sticky left-0 z-20 bg-gray-50 px-3 py-2 text-left font-medium text-gray-500 min-w-[160px] border-r border-gray-200">
                  Judge
                </th>
                <th className="sticky left-[160px] z-20 bg-gray-50 px-2 py-2 text-center font-medium text-gray-500 w-12 border-r border-gray-200">
                  #
                </th>
                {filteredProjects.map(p => {
                  const count = projectCounts.get(p.Project_ID) || 0;
                  const headerColor = count < judgesPerProject
                    ? 'text-amber-600'
                    : count === judgesPerProject
                      ? 'text-green-600'
                      : 'text-gray-500';
                  return (
                    <th
                      key={p.Project_ID}
                      className={`px-0.5 py-2 text-center font-medium min-w-[40px] ${headerColor}`}
                      title={`${p.Project_Number}: ${p.Presenter_Display_Name || `${p.Presenter_First_Name} ${p.Presenter_Last_Name}`} (${count}/${judgesPerProject} judges)`}
                    >
                      <div className="[writing-mode:vertical-lr] rotate-180 mx-auto whitespace-nowrap text-[10px] h-16 flex items-center justify-center">
                        {p.Project_Number}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {judges.map(j => (
                <tr key={j.Judge_ID} className="hover:bg-blue-50/30">
                  <td className="sticky left-0 z-10 bg-white px-3 py-1.5 font-medium whitespace-nowrap border-r border-gray-200 text-gray-800">
                    {j.First_Name} {j.Last_Name}
                  </td>
                  <td className="sticky left-[160px] z-10 bg-white px-2 py-1.5 text-center font-mono text-gray-500 border-r border-gray-200">
                    {judgeTotals.get(j.Judge_ID) || 0}
                  </td>
                  {filteredProjects.map(p => {
                    const key = `${j.Judge_ID}:${p.Project_ID}`;
                    const isAssigned = assignmentMap.has(key);
                    const isToggling = toggling.has(key);
                    return (
                      <td key={p.Project_ID} className="px-0.5 py-1.5 text-center">
                        <input
                          type="checkbox"
                          checked={isAssigned}
                          disabled={isToggling}
                          onChange={() => handleToggle(j.Judge_ID, p.Project_ID)}
                          className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer disabled:opacity-50"
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-gray-50 border-t border-gray-200">
                <td className="sticky left-0 z-10 bg-gray-50 px-3 py-2 font-medium text-gray-500 border-r border-gray-200">
                  Judges/Project
                </td>
                <td className="sticky left-[160px] z-10 bg-gray-50 px-2 py-2 text-center font-mono text-gray-500 border-r border-gray-200">
                  &Sigma;
                </td>
                {filteredProjects.map(p => {
                  const count = projectCounts.get(p.Project_ID) || 0;
                  const colorClass = count === 0
                    ? 'text-gray-400'
                    : count < judgesPerProject
                      ? 'text-amber-600 font-bold'
                      : count === judgesPerProject
                        ? 'text-green-600 font-bold'
                        : 'text-blue-600 font-bold';
                  return (
                    <td key={p.Project_ID} className={`px-0.5 py-2 text-center font-mono ${colorClass}`}>
                      {count}
                    </td>
                  );
                })}
              </tr>
            </tfoot>
          </table>
        </div>
        {filteredProjects.length === 0 && (
          <div className="text-center py-8 text-gray-400">No projects in this category</div>
        )}
      </div>
    </div>
  );
}
