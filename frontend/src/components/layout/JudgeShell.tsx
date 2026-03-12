import { Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function JudgeShell() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-4 py-4 sm:px-6 sm:py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900 sm:text-lg">
              GPSA Symposium
            </h1>
            <p className="text-sm text-gray-500 sm:text-xs">
              Graduate Student Symposium 2026
            </p>
          </div>
          {user && (
            <div className="flex items-center gap-3">
              <span className="text-base text-gray-600 sm:text-sm">{user.name}</span>
              <button
                onClick={() => {
                  logout();
                  window.location.href = '/judge';
                }}
                className="text-base text-red-600 hover:text-red-800 sm:text-sm"
              >
                Exit
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-3xl p-4 sm:p-4">
        <Outlet />
      </main>
    </div>
  );
}
