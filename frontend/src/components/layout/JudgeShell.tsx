import { Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function JudgeShell() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-gray-900">GPSA Symposium</h1>
          <p className="text-xs text-gray-500">Graduate Student Symposium 2026</p>
        </div>
        {user && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{user.name}</span>
            <button
              onClick={() => { logout(); window.location.href = '/judge'; }}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Exit
            </button>
          </div>
        )}
      </header>

      <main className="p-4 max-w-2xl mx-auto">
        <Outlet />
      </main>
    </div>
  );
}
