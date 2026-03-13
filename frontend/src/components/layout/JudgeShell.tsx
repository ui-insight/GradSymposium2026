import { Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function JudgeShell() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(241,179,0,0.22),_transparent_26%),linear-gradient(180deg,_#fffdf8_0%,_#efe5d4_100%)]">
      <header className="border-b border-[#3c3320] bg-[#111111] px-4 py-4 sm:px-6 sm:py-4">
        <div className="mx-auto flex max-w-5xl items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-white px-4 py-3 shadow-sm">
              <img
                src="/uidaho-logo-horizontal.png"
                alt="University of Idaho"
                className="h-8 w-auto sm:h-10"
              />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#f5d36e]">
                Judge Portal
              </p>
              <h1 className="mt-1 text-xl font-semibold text-white sm:text-lg">
                GPSA Graduate Student Symposium
              </h1>
              <p className="text-sm text-[#d7ccb9] sm:text-xs">
                March 13, 2026 · Bruce Pitman Center
              </p>
            </div>
          </div>
          {user && (
            <div className="flex items-center gap-3 rounded-2xl border border-[#3c3320] bg-[#171717] px-4 py-3">
              <span className="text-base text-[#f5efe0] sm:text-sm">{user.name}</span>
              <button
                onClick={() => {
                  logout();
                  window.location.href = '/judge';
                }}
                className="text-base font-medium text-[#f2c94c] hover:text-white sm:text-sm"
              >
                Exit
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
        <div className="rounded-[2rem] border border-white/60 bg-white/70 p-4 shadow-sm backdrop-blur sm:p-5">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
