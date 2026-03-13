import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const navItems = [
  { path: '/admin/dashboard', label: 'Dashboard' },
  { path: '/admin/projects', label: 'Projects' },
  { path: '/admin/judges', label: 'Judges' },
  { path: '/admin/assignments', label: 'Assignments' },
  { path: '/admin/rubrics', label: 'Rubrics' },
  { path: '/admin/results', label: 'Results' },
];

export function AdminShell() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(241,179,0,0.16),_transparent_30%),linear-gradient(180deg,_#f7f2e7_0%,_#efe5d5_100%)] lg:flex">
      <aside className="flex w-full flex-col border-b border-[#3c3320] bg-[#111111] text-white lg:min-h-screen lg:w-72 lg:border-b-0 lg:border-r">
        <div className="border-b border-[#3c3320] px-6 py-6">
          <div className="rounded-2xl bg-white px-4 py-4 shadow-sm">
            <img
              src="/uidaho-logo-horizontal.png"
              alt="University of Idaho"
              className="h-10 w-auto"
            />
          </div>
          <div className="mt-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#f5d36e]">
              Graduate Student Symposium
            </p>
            <h1 className="mt-2 text-xl font-semibold text-white">Administration Hub</h1>
            <p className="mt-2 text-sm leading-6 text-[#d7ccb9]">
              Real-time event operations for judges, projects, assignments and results.
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-4 py-5">
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`block rounded-xl px-4 py-3 text-sm font-medium transition-colors ${
                location.pathname === item.path
                  ? 'bg-[#f1b300] text-black shadow-sm'
                  : 'text-[#e7dfcf] hover:bg-[#221d13] hover:text-white'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="border-t border-[#3c3320] px-4 py-5">
          <div className="rounded-2xl border border-[#3c3320] bg-[#171717] px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#f5d36e]">
              Signed In
            </p>
            <p className="mt-2 text-sm font-medium text-white">{user?.name}</p>
          </div>
          <button
            onClick={() => { logout(); window.location.href = '/admin/login'; }}
            className="mt-3 text-sm font-medium text-[#f2c94c] hover:text-white"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="rounded-[2rem] border border-white/50 bg-white/55 p-4 shadow-sm backdrop-blur md:p-6">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
