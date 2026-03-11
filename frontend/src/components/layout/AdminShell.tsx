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
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-lg font-bold text-gray-900">Symposium Admin</h1>
          <p className="text-sm text-gray-500">GPSA 2026</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`block px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === item.path
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-200">
          <p className="text-sm text-gray-500 mb-2">{user?.name}</p>
          <button
            onClick={() => { logout(); window.location.href = '/admin/login'; }}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
