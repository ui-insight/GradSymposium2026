import { PosterLocation } from '../components/PosterLocation';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { conferenceDates, fetchPosterDirectory } from '../api/publicPosters';
import type { PublicPosterDirectory } from '../types';

function normalize(value: string): string {
  return value.normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase().trim();
}

export function PosterLookupPage() {
  const [directory, setDirectory] = useState<PublicPosterDirectory | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(() => params.get('q') || '');

  function saveSearchLink() {
    const next = new URLSearchParams(params);
    if (search) next.set('q', search); else next.delete('q');
    setParams(next, { replace: true });
  }

  useEffect(() => {
    const controller = new AbortController();
    fetchPosterDirectory(controller.signal)
      .then(data => { setDirectory(data); setError(''); })
      .catch((err: Error) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    const previous = document.title;
    document.title = `Find my poster | ${directory?.event?.Event_Name || 'University of Idaho'}`;
    return () => { document.title = previous; };
  }, [directory?.event?.Event_Name]);

  const query = normalize(search);
  const matches = (directory?.posters || []).filter(poster => {
    const text = normalize(`${poster.Project_Number} ${poster.Presenter_Display_Name} ${poster.Project_Title} ${poster.Institution || ''}`);
    const numberQuery = query.match(/^(?:p[-\s]*)?0*(\d+)$/);
    const posterNumber = poster.Project_Number.match(/^P-0*(\d+)$/i);
    return !query || query.split(/\s+/).every(word => text.includes(word))
      || Boolean(numberQuery && posterNumber && Number(numberQuery[1]) === Number(posterNumber[1]));
  });

  return (
    <div className="min-h-screen bg-[oklch(0.98_0.008_85)] text-[oklch(0.23_0.008_85)]">
      <header className="border-b border-[oklch(0.85_0.025_85)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-5 sm:px-8">
          <Link to="/" aria-label="Conference home" className="rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-700">
            <img src="/uidaho-logo-horizontal.png" alt="University of Idaho" className="h-9 w-auto max-w-[190px] sm:h-11" />
          </Link>
          <Link to="/judge" className="flex min-h-11 items-center rounded px-2 text-sm font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-amber-700 print:hidden">Judge sign in</Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 pb-16 pt-10 sm:px-8 sm:pt-14">
        <p className="max-w-[70ch] text-sm font-semibold text-[oklch(0.42_0.04_85)]">
          {directory?.event?.Event_Name || 'Conference poster directory'}
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">Find my poster</h1>
        {directory?.event && <p className="mt-4 max-w-[70ch] text-sm leading-6 text-[oklch(0.42_0.015_85)]">{conferenceDates(directory.event)}{directory.event.Location && ` · ${directory.event.Location}`}</p>}

        {directory?.is_draft_preview && <aside aria-label="Draft roster notice" className="mt-6 border border-amber-300 bg-amber-50 p-5 text-amber-950">
          <h2 className="font-semibold">Dev preview: unconfirmed draft roster</h2>
          <p className="mt-2 max-w-[70ch] text-sm leading-6">This list includes possible duplicates and talk-only submissions for organizer review. Candidate numbers identify source submissions; they do not confirm poster acceptance. Locations have not been assigned.</p>
        </aside>}

        {error ? (
          <div role="alert" className="mt-8 rounded-xl border border-red-300 bg-red-50 p-5">
            <p>{error}</p>
            <button onClick={() => { setError(''); setAttempt(value => value + 1); }} className="mt-3 min-h-11 rounded-lg bg-[oklch(0.25_0.008_85)] px-5 font-semibold text-[oklch(0.98_0.008_85)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-700">Try again</button>
          </div>
        ) : !directory ? (
          <div role="status" aria-label="Loading poster directory" className="mt-9 space-y-5">
            <p>Loading poster directory…</p>
            {[1, 2, 3].map(row => <div key={row} className="h-24 rounded-lg bg-[oklch(0.94_0.015_85)]" aria-hidden="true" />)}
          </div>
        ) : !directory.event || directory.posters.length === 0 ? (
          <div className="mt-9 max-w-[65ch] border-t border-[oklch(0.85_0.025_85)] pt-7">
            <h2 className="text-xl font-semibold">Poster numbers are being prepared</h2>
            <p className="mt-3 leading-7 text-[oklch(0.42_0.015_85)]">The organizers will publish the directory when the roster is ready. Please check back, or visit the registration desk for help.</p>
            <button onClick={() => setAttempt(value => value + 1)} className="mt-4 min-h-11 rounded px-1 font-semibold underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-amber-700">Check again</button>
          </div>
        ) : (
          <>
            <div className="mt-9 print:hidden">
              <label htmlFor="poster-search" className="block text-sm font-semibold">Search by name, poster title, number, or institution</label>
              <input id="poster-search" type="search" value={search} onChange={event => setSearch(event.target.value)} onBlur={saveSearchLink} onKeyDown={event => { if (event.key === 'Enter') saveSearchLink(); }} placeholder="For example, your last name or P-042" autoComplete="off" className="mt-3 min-h-14 w-full rounded-xl border border-[oklch(0.65_0.03_85)] bg-[oklch(0.995_0.005_85)] px-4 text-base sm:text-lg" />
            </div>
            <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-b border-[oklch(0.78_0.025_85)] pb-4">
              <p role="status" aria-live="polite" className="text-sm text-[oklch(0.42_0.015_85)]">{matches.length} {matches.length === 1 ? 'poster' : 'posters'}{query ? ` matching “${search}”` : ' in the directory'}</p>
              {matches.length > 0 && <button onClick={() => window.print()} className="min-h-11 rounded px-2 text-sm font-semibold underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-amber-700 print:hidden">Print this list</button>}
            </div>
            {matches.length === 0 ? (
              <div className="py-10">
                <h2 className="text-xl font-semibold">No matching posters</h2>
                <p className="mt-3 max-w-[65ch] leading-7">Try part of your name or title. If your poster is missing, visit the registration desk.</p>
                <button onClick={() => { setSearch(''); setParams({}); document.getElementById('poster-search')?.focus(); }} className="mt-4 min-h-11 rounded-lg bg-[oklch(0.83_0.16_85)] px-5 font-semibold hover:bg-[oklch(0.78_0.16_85)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-700">Clear search</button>
              </div>
            ) : (
              <ul aria-label="Posters" className="divide-y divide-[oklch(0.85_0.025_85)]">
                {matches.map(poster => <li key={poster.Project_Number} className="grid break-inside-avoid gap-4 py-7 sm:grid-cols-[8rem_1fr] sm:gap-7">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-[oklch(0.42_0.04_85)]">{directory.is_draft_preview ? 'Candidate number' : 'Poster number'}</span>
                    <p className="mt-1 font-mono text-3xl font-bold">{poster.Project_Number}</p>
                    <PosterLocation poster={poster} />
                  </div>
                  <div className="min-w-0 break-words">
                    <h2 className="text-xl font-semibold leading-7">{poster.Presenter_Display_Name}</h2>
                    {poster.Institution && <p className="mt-1 text-sm text-[oklch(0.42_0.015_85)]">{poster.Institution}</p>}
                    <p className="mt-3 max-w-[70ch] text-base leading-7">{poster.Project_Title}</p>
                  </div>
                </li>)}
              </ul>
            )}
          </>
        )}
      </main>
    </div>
  );
}
