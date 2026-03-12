import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import type { JudgeProject } from '../../types';

export function JudgeProjectListPage() {
  const [projects, setProjects] = useState<JudgeProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [view, setView] = useState<'assigned' | 'all'>('assigned');

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const p = await apiFetch<JudgeProject[]>('/judge/projects');
      setProjects(p);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }

  const filtered = projects.filter(p => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      p.Project_Number.toLowerCase().includes(term) ||
      p.Project_Title.toLowerCase().includes(term) ||
      `${p.Presenter_First_Name} ${p.Presenter_Last_Name}`.toLowerCase().includes(term)
    );
  });

  const assigned = filtered.filter(p => p.is_assigned);
  const displayProjects = view === 'assigned' ? assigned : filtered;
  const scoredCount = assigned.filter(p => p.is_scored).length;

  if (loading) return <div className="text-center py-8 text-gray-500">Loading projects...</div>;

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900 sm:text-xl">
        Projects to Score
      </h1>

      {assigned.length > 0 && (
        <p className="mb-4 text-base text-gray-500 sm:text-sm">
          {scoredCount} of {assigned.length} assigned projects scored
        </p>
      )}

      {/* View toggle */}
      <div className="mb-4 flex flex-wrap gap-2">
        <button
          onClick={() => setView('assigned')}
          className={`rounded-full px-4 py-2 text-base font-medium transition-colors sm:px-3 sm:py-1.5 sm:text-sm ${
            view === 'assigned'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          My Assignments ({assigned.length})
        </button>
        <button
          onClick={() => setView('all')}
          className={`rounded-full px-4 py-2 text-base font-medium transition-colors sm:px-3 sm:py-1.5 sm:text-sm ${
            view === 'all'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          All Projects ({projects.length})
        </button>
      </div>

      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search projects..."
        className="mb-4 w-full rounded-lg border border-gray-300 px-4 py-3 text-base outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 sm:py-2 sm:text-sm"
      />

      <div className="space-y-2">
        {displayProjects.map(p => <ProjectCard key={p.Project_ID} project={p} />)}
      </div>

      {displayProjects.length === 0 && (
        <div className="text-center py-8 text-gray-400">
          {view === 'assigned' ? 'No projects assigned to you yet' : 'No projects found'}
        </div>
      )}
    </div>
  );
}

function ProjectCard({ project: p }: { project: JudgeProject }) {
  return (
    <Link
      to={`/judge/projects/${p.Project_ID}`}
      className="block rounded-xl border border-gray-200 bg-white p-4 transition-colors hover:border-blue-300 sm:p-4"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl font-mono font-bold text-gray-900 sm:text-lg">
              {p.Project_Number}
            </span>
            <span className={`rounded-full px-2 py-1 text-sm font-medium sm:py-0.5 sm:text-xs ${
              p.Category === 'Art' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
            }`}>{p.Category}</span>
            {p.is_scored && (
              <span className="rounded-full bg-green-100 px-2 py-1 text-sm font-medium text-green-700 sm:py-0.5 sm:text-xs">
                Scored
              </span>
            )}
          </div>
          <p className="truncate text-base text-gray-700 sm:text-sm">{p.Project_Title}</p>
          <p className="mt-1 text-sm text-gray-500 sm:text-xs">
            {p.Presenter_First_Name} {p.Presenter_Last_Name}
            {p.Department && ` — ${p.Department}`}
          </p>
        </div>
        {p.Table_Number && (
          <span className="ml-2 text-sm text-gray-400 sm:text-xs">{p.Table_Number}</span>
        )}
      </div>
    </Link>
  );
}
