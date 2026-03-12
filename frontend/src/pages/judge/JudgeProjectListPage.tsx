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
      <h1 className="text-xl font-bold text-gray-900 mb-2">Projects to Score</h1>

      {assigned.length > 0 && (
        <p className="text-sm text-gray-500 mb-4">
          {scoredCount} of {assigned.length} assigned projects scored
        </p>
      )}

      {/* View toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setView('assigned')}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            view === 'assigned'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          My Assignments ({assigned.length})
        </button>
        <button
          onClick={() => setView('all')}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
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
        className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
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
      className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg font-mono font-bold text-gray-900">{p.Project_Number}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              p.Category === 'Art' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
            }`}>{p.Category}</span>
            {p.is_scored && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Scored</span>
            )}
          </div>
          <p className="text-sm text-gray-700 truncate">{p.Project_Title}</p>
          <p className="text-xs text-gray-500 mt-1">
            {p.Presenter_First_Name} {p.Presenter_Last_Name}
            {p.Department && ` — ${p.Department}`}
          </p>
        </div>
        {p.Table_Number && (
          <span className="text-xs text-gray-400 ml-2">{p.Table_Number}</span>
        )}
      </div>
    </Link>
  );
}
