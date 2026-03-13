import { Link } from 'react-router-dom';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0f0f0f] px-4 py-8 text-white">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1.2fr_0.9fr]">
          <section className="relative overflow-hidden rounded-[2rem] border border-[#3c3320] bg-[linear-gradient(135deg,_rgba(241,179,0,0.18),_transparent_30%),linear-gradient(180deg,_#171717_0%,_#0f0f0f_100%)] p-8 shadow-2xl sm:p-10">
            <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-[#f1b300]/20 blur-3xl" />
            <div className="relative max-w-2xl">
              <div className="inline-flex rounded-2xl bg-white px-4 py-3 shadow-sm">
                <img
                  src="/uidaho-logo-horizontal.png"
                  alt="University of Idaho"
                  className="h-10 w-auto sm:h-12"
                />
              </div>
              <p className="mt-8 text-xs font-semibold uppercase tracking-[0.26em] text-[#f5d36e]">
                Boldly toward discovery
              </p>
              <h1 className="mt-4 text-4xl font-semibold leading-tight text-white sm:text-5xl">
                GPSA Graduate Student Symposium 2026
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-[#ddd2bf] sm:text-lg">
                Scoring, rankings and event operations for the University of Idaho’s
                graduate research and creative work showcase.
              </p>
              <div className="mt-8 flex flex-wrap gap-3 text-sm text-[#e6dcc8]">
                <span className="rounded-full border border-[#4b4028] px-4 py-2">
                  March 13, 2026
                </span>
                <span className="rounded-full border border-[#4b4028] px-4 py-2">
                  Bruce Pitman Center
                </span>
                <span className="rounded-full border border-[#4b4028] px-4 py-2">
                  International Ballroom
                </span>
              </div>
            </div>
          </section>

          <section className="flex items-center">
            <div className="w-full rounded-[2rem] border border-[#d9ccb0] bg-[rgba(255,252,245,0.96)] p-6 text-left shadow-2xl backdrop-blur sm:p-8">
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-[#8b6200]">
                Access
              </p>
              <h2 className="mt-3 text-3xl font-semibold text-gray-900">
                Choose your entry point
              </h2>
              <p className="mt-3 text-sm leading-6 text-gray-600">
                Judges use access codes on-site. Administrators manage assignments,
                monitor results and review score details.
              </p>

              <div className="mt-8 space-y-4">
          <Link
            to="/judge"
                  className="block rounded-[1.5rem] border border-[#2d2414] bg-[#111111] px-5 py-5 text-white transition-colors hover:bg-[#1b1b1b]"
          >
                  <span className="block text-lg font-semibold">Judge Scoring Portal</span>
                  <span className="mt-1 block text-sm font-normal text-[#d9cba9]">
                    Enter your access code to score presentations and submit feedback.
                  </span>
          </Link>

          <Link
            to="/admin/login"
                  className="block rounded-[1.5rem] border border-[#d8c8a6] bg-[#f5efe1] px-5 py-5 text-gray-900 transition-colors hover:bg-[#efe5d3]"
          >
                  <span className="block text-lg font-semibold">Admin Dashboard</span>
                  <span className="mt-1 block text-sm font-normal text-gray-600">
                    Manage judges, projects, assignments, rubrics and live results.
                  </span>
          </Link>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
