import { useState, useEffect } from 'react';
import { apiFetch } from '../../api/client';
import type { Judge, Project, Event, Assignment } from '../../types';

export function AssignmentsPage() {
  const [judges, setJudges] = useState<Judge[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('Poster');
  const [judgesPerProject, setJudgesPerProject] = useState(3);
  const [assignmentMap, setAssignmentMap] = useState<Map<string, number>>(new Map());
  const [toggling, setToggling] = useState<Set<string>>(new Set());

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const ev = await apiFetch<Event | null>('/events/active');
      setEvent(ev);
      if (ev) {
        const [j, p, a] = await Promise.all([
          apiFetch<Judge[]>(`/judges/?event_id=${ev.Event_ID}`),
          apiFetch<Project[]>(`/projects/?event_id=${ev.Event_ID}`),
          apiFetch<Assignment[]>(`/assignments/?event_id=${ev.Event_ID}`),
        ]);
        setJudges(j);
        setProjects(p);
        const map = new Map<string, number>();
        for (const assignment of a) {
          map.set(`${assignment.Judge_ID}:${assignment.Project_ID}`, assignment.Assignment_ID);
        }
        setAssignmentMap(map);
      }
    } catch (err) { console.error(err); }
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
    } catch (err) { console.error(err); }
    finally {
      setToggling(prev => { const s = new Set(prev); s.delete(key); return s; });
    }
  }

  async function handleAutoAssign() {
    if (!event) return;

    const targetProjects = filteredProjects;

    // Build current assignment counts per judge (across ALL projects, not just filtered)
    const judgeCounts = new Map<string, number>();
    judges.forEach(j => judgeCounts.set(j.Judge_ID, 0));
    for (const key of assignmentMap.keys()) {
      const judgeId = key.split(':')[0];
      judgeCounts.set(judgeId, (judgeCounts.get(judgeId) || 0) + 1);
    }

    const newAssignments: { Judge_ID: string; Project_ID: string }[] = [];

    for (const project of targetProjects) {
      const alreadyAssigned = new Set(
        [...assignmentMap.keys()]
          .filter(k => k.endsWith(`:${project.Project_ID}`))
          .map(k => k.split(':')[0])
      );

      const needed = judgesPerProject - alreadyAssigned.size;
      if (needed <= 0) continue;

      const available = judges
        .filter(j => !alreadyAssigned.has(j.Judge_ID))
        .sort((a, b) => (judgeCounts.get(a.Judge_ID) || 0) - (judgeCounts.get(b.Judge_ID) || 0));

      for (let i = 0; i < Math.min(needed, available.length); i++) {
        const judge = available[i];
        newAssignments.push({ Judge_ID: judge.Judge_ID, Project_ID: project.Project_ID });
        judgeCounts.set(judge.Judge_ID, (judgeCounts.get(judge.Judge_ID) || 0) + 1);
      }
    }

    if (newAssignments.length === 0) return;

    try {
      await apiFetch('/assignments/bulk', {
        method: 'POST',
        body: JSON.stringify({ assignments: newAssignments }),
      });
      await loadData();
    } catch (err) { console.error(err); }
  }

  async function handleClearAll() {
    if (!event || !confirm('Remove all judge assignments? This cannot be undone.')) return;
    try {
      await apiFetch(`/assignments/clear?event_id=${event.Event_ID}`, { method: 'DELETE' });
      setAssignmentMap(new Map());
    } catch (err) { console.error(err); }
  }

  const filteredProjects = projects
    .filter(p => !filter || p.Category === filter)
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
          max={judges.length}
          value={judgesPerProject}
          onChange={e => setJudgesPerProject(Number(e.target.value))}
          className="w-16 px-2 py-1.5 border border-gray-300 rounded-lg text-sm text-center"
        />
        <span className="text-sm text-gray-500">judges per {filter || 'all'} project</span>
        <button
          onClick={handleAutoAssign}
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
                {filteredProjects.map(p => (
                  <th
                    key={p.Project_ID}
                    className="px-0.5 py-2 text-center font-medium text-gray-500 min-w-[40px]"
                    title={`${p.Project_Number}: ${p.Presenter_First_Name} ${p.Presenter_Last_Name}`}
                  >
                    <div className="[writing-mode:vertical-lr] rotate-180 mx-auto whitespace-nowrap text-[10px] h-16 flex items-center justify-center">
                      {p.Project_Number}
                    </div>
                  </th>
                ))}
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
                {filteredProjects.map(p => (
                  <td key={p.Project_ID} className="px-0.5 py-2 text-center font-mono text-gray-500">
                    {projectCounts.get(p.Project_ID) || 0}
                  </td>
                ))}
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
