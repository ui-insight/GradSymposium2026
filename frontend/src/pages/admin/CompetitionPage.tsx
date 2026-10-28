import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { getSelectedEvent } from '../../api/event';
import type { Event, Judge, Project } from '../../types';
import type {
  CompetitionSettings,
  CompetitionStatus,
  JudgeConflict,
} from '../../types/competition';
import {
  actionClass,
  fieldClass,
  sectionClass,
  nullableBool,
  boolValue,
} from '../../utils/competitionUi';

export function CompetitionPage() {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get('event_id');
  const [event, setEvent] = useState<Event | null>(null);
  const [options, setOptions] = useState<
    { Event_ID: string; Event_Name: string }[]
  >([]);
  const [state, setState] = useState<CompetitionStatus | null>(null);
  const [draft, setDraft] = useState<CompetitionSettings | null>(null);
  const [groups, setGroups] = useState('');
  const [judges, setJudges] = useState<Judge[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [conflicts, setConflicts] = useState<JudgeConflict[]>([]);
  const [conflictJudge, setConflictJudge] = useState('');
  const [conflictProject, setConflictProject] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [onlyMissing, setOnlyMissing] = useState(false);

  const load = useCallback(
    async (resetDraft = false) => {
      const [ev, active, demos] = await Promise.all([
        getSelectedEvent(selectedId),
        apiFetch<Event | null>('/events/active'),
        apiFetch<{ Event_ID: string; Event_Name: string }[]>(
          '/competition/rehearsals/list',
        ),
      ]);
      setEvent(ev);
      setOptions([
        ...(active ? [active] : []),
        ...demos.filter((d) => d.Event_ID !== active?.Event_ID),
      ]);
      if (!ev) return;
      const [status, nextJudges, nextProjects, nextConflicts] =
        await Promise.all([
          apiFetch<CompetitionStatus>(`/competition/${ev.Event_ID}`),
          apiFetch<Judge[]>(`/judges/?event_id=${ev.Event_ID}`),
          apiFetch<Project[]>(`/projects/?event_id=${ev.Event_ID}`),
          apiFetch<JudgeConflict[]>(`/competition/${ev.Event_ID}/conflicts`),
        ]);
      setState(status);
      setJudges(nextJudges);
      setProjects(nextProjects);
      setConflicts(nextConflicts);
      if (resetDraft) {
        setDraft(status.settings);
        setGroups((status.settings.Award_Groups || []).join(', '));
      }
    },
    [selectedId],
  );

  useEffect(() => {
    setLoading(true);
    load(true)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [load]);
  useEffect(() => {
    const timer = setInterval(
      () => load(false).catch((err) => setError(err.message)),
      10000,
    );
    return () => clearInterval(timer);
  }, [load]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The action failed.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p role="status">Loading competition setup…</p>;
  if (!event || !state || !draft)
    return <div role="alert">{error || 'No event is available.'}</div>;
  const query = `?event_id=${encodeURIComponent(event.Event_ID)}`;
  const visible = state.coverage.filter(
    (row) =>
      (!onlyMissing ||
        (row.Missing_Reviews !== null && row.Missing_Reviews > 0)) &&
      `${row.Project_Number} ${row.Presenter_Display_Name} ${row.Project_Title}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );

  return (
    <div>
      <h1 className="text-2xl font-bold">Competition setup</h1>
      <p className="mt-2 max-w-[70ch] text-sm leading-6 text-gray-600">
        Prepare judging without choosing unconfirmed rules. Review coverage
        updates every 10 seconds and counts complete, valid score sheets.
      </p>
      <label className="mt-5 block max-w-xl text-sm font-semibold">
        Event
        <select
          className={fieldClass}
          value={event.Event_ID}
          onChange={(e) => {
            setError('');
            setNotice('');
            setParams({ event_id: e.target.value });
          }}
        >
          {options.map((option) => (
            <option key={option.Event_ID} value={option.Event_ID}>
              {option.Event_Name}
            </option>
          ))}
        </select>
      </label>
      {state.Is_Rehearsal && (
        <p className="mt-4 border border-amber-300 bg-amber-50 p-4 text-sm">
          Synthetic rehearsal only. The example rubric, targets, and ballot
          rules are test data and do not define the ASM competition.
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="mt-4 border border-red-300 bg-red-50 p-4 text-red-800"
        >
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="mt-4 border border-gray-300 p-4">
          {notice}
        </p>
      )}
      <nav aria-label="Competition tools" className="my-5 flex flex-wrap gap-2">
        {[
          ['projects', 'Eligibility / roster'],
          ['judges', 'Judges'],
          ['assignments', 'Assignments'],
          ['rubrics', 'Rubric'],
          ['results', 'Results'],
          ['voting', 'Attendee voting'],
        ].map(([path, label]) => (
          <Link
            className={actionClass}
            key={path}
            to={`/admin/${path}${query}`}
          >
            {label}
          </Link>
        ))}
      </nav>

      <section className={sectionClass} aria-labelledby="readiness-heading">
        <h2 id="readiness-heading" className="text-xl font-semibold">
          {state.settings.Judging_Open
            ? 'Judging is open'
            : 'Judging is closed'}
        </h2>
        {state.missing.length ? (
          <>
            <p className="mt-3 text-sm font-semibold">
              Still needed before opening:
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6">
              {state.missing.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        ) : (
          <p className="mt-3 text-sm">The configured readiness checks pass.</p>
        )}
        <p className="mt-4 text-sm text-gray-600">
          {state.Active_Judges} active judges · {state.Eligible_Projects}{' '}
          eligible presentations · {state.Complete_Reviews} complete reviews ·{' '}
          {state.Projects_At_Target} presentations at the review target
        </p>
        <div className="mt-4 flex gap-2">
          <button
            className={actionClass}
            disabled={
              busy || state.missing.length > 0 || state.settings.Judging_Open
            }
            onClick={() =>
              run(async () => {
                await apiFetch(`/competition/${event.Event_ID}/open`, {
                  method: 'POST',
                });
                setNotice('Judging opened.');
              })
            }
          >
            Open judging
          </button>
          <button
            className={actionClass}
            disabled={busy || !state.settings.Judging_Open}
            onClick={() =>
              run(async () => {
                await apiFetch(`/competition/${event.Event_ID}/close`, {
                  method: 'POST',
                });
                setNotice('Judging closed.');
              })
            }
          >
            Close judging
          </button>
        </div>
      </section>

      <form
        className={sectionClass}
        onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            await apiFetch(`/competition/${event.Event_ID}/settings`, {
              method: 'PUT',
              body: JSON.stringify({
                Required_Reviews: draft.Required_Reviews,
                Assignment_Only: draft.Assignment_Only,
                Aggregation: draft.Aggregation,
                Tie_Policy: draft.Tie_Policy,
                Award_Groups: groups.trim()
                  ? groups.split(',').map((group) => group.trim())
                  : draft.Award_Groups,
                Rules_Confirmed: draft.Rules_Confirmed,
              }),
            });
            setNotice(
              'Judging rules saved. Opening judging remains a separate action.',
            );
          });
        }}
      >
        <h2 className="text-xl font-semibold">Judging rules</h2>
        <p className="mt-2 max-w-[70ch] text-sm leading-6 text-gray-600">
          Leave choices pending until confirmed. Rubric criteria and rules
          freeze after the first score. The current scoring system supports
          integer criterion scores within each rubric’s range (up to 0–5).
        </p>
        <fieldset
          disabled={busy || state.settings.Judging_Open}
          className="mt-5 grid gap-5 sm:grid-cols-2"
        >
          <label className="text-sm font-semibold">
            Required complete reviews per presentation
            <input
              className={fieldClass}
              type="number"
              min="1"
              max="100"
              placeholder="Pending confirmation"
              value={draft.Required_Reviews ?? ''}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  Required_Reviews: e.target.value
                    ? Number(e.target.value)
                    : null,
                })
              }
            />
          </label>
          <label className="text-sm font-semibold">
            May judges score only their assignments?
            <select
              className={fieldClass}
              value={boolValue(draft.Assignment_Only)}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  Assignment_Only: nullableBool(e.target.value),
                })
              }
            >
              <option value="">Pending confirmation</option>
              <option value="true">Yes, assignments restrict scoring</option>
              <option value="false">No, any eligible presentation</option>
            </select>
          </label>
          <label className="text-sm font-semibold">
            Aggregate complete reviews by
            <select
              className={fieldClass}
              value={draft.Aggregation || ''}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  Aggregation:
                    (e.target.value as CompetitionSettings['Aggregation']) ||
                    null,
                })
              }
            >
              <option value="">Pending confirmation</option>
              <option value="average">Average judge total</option>
              <option value="total">Sum of judge totals</option>
            </select>
          </label>
          <label className="text-sm font-semibold">
            Tie handling
            <select
              className={fieldClass}
              value={draft.Tie_Policy || ''}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  Tie_Policy:
                    (e.target.value as CompetitionSettings['Tie_Policy']) ||
                    null,
                })
              }
            >
              <option value="">Pending confirmation</option>
              <option value="shared">Share ranks (1, 1, 3)</option>
              <option value="manual">Flag ties for organizer resolution</option>
            </select>
          </label>
          <label className="text-sm font-semibold sm:col-span-2">
            Award group names, separated by commas
            <input
              className={fieldClass}
              value={groups}
              onChange={(e) => {
                setGroups(e.target.value);
                setDraft({
                  ...draft,
                  Award_Groups: e.target.value.trim()
                    ? e.target.value.split(',').map((v) => v.trim())
                    : null,
                });
              }}
              placeholder="Pending confirmation"
            />
          </label>
          <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={
                draft.Award_Groups !== null && draft.Award_Groups.length === 0
              }
              onChange={(e) => {
                setGroups('');
                setDraft({
                  ...draft,
                  Award_Groups: e.target.checked ? [] : null,
                });
              }}
            />
            Organizer confirmed there are no separate award groups
          </label>
          <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={draft.Rules_Confirmed}
              onChange={(e) =>
                setDraft({ ...draft, Rules_Confirmed: e.target.checked })
              }
            />
            Organizer has confirmed these judging rules
          </label>
          <button className={`${actionClass} justify-self-start`} type="submit">
            Save rules
          </button>
        </fieldset>
      </form>

      <section className={sectionClass} aria-labelledby="coverage-heading">
        <h2 id="coverage-heading" className="text-xl font-semibold">
          Review coverage
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Assignments and completed reviews are counted separately. A partial
          score sheet does not count toward the target.
        </p>
        <label className="mt-4 block text-sm font-semibold">
          Find a presentation
          <input
            className={fieldClass}
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Number, presenter, or title"
          />
        </label>
        <label className="my-3 flex min-h-11 items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={onlyMissing}
            onChange={(e) => setOnlyMissing(e.target.checked)}
          />
          Show presentations below the review target
        </label>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">
              Complete review coverage by presentation
            </caption>
            <thead>
              <tr>
                {[
                  'Presentation',
                  'Eligibility',
                  'Assigned',
                  'Complete',
                  'Target',
                  'Still needed',
                ].map((label) => (
                  <th
                    key={label}
                    className="border-b border-gray-300 px-3 py-3"
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.Project_ID}>
                  <td className="border-b border-gray-200 px-3 py-4">
                    <span className="font-mono font-semibold">
                      {row.Project_Number}
                    </span>
                    <p className="mt-1">{row.Presenter_Display_Name}</p>
                  </td>
                  <td className="border-b border-gray-200 px-3 py-4">
                    {row.Judging_Eligible === null
                      ? 'Pending'
                      : row.Judging_Eligible
                        ? 'Eligible'
                        : 'Excluded'}
                  </td>
                  <td className="border-b border-gray-200 px-3 py-4">
                    {row.Assigned_Judges}
                  </td>
                  <td className="border-b border-gray-200 px-3 py-4">
                    {row.Complete_Reviews}
                  </td>
                  <td className="border-b border-gray-200 px-3 py-4">
                    {row.Required_Reviews ?? 'Pending'}
                  </td>
                  <td className="border-b border-gray-200 px-3 py-4">
                    {row.Missing_Reviews ?? 'Pending'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {visible.length === 0 && (
            <p className="py-5 text-sm">
              No presentations match these filters.
            </p>
          )}
        </div>
      </section>

      <section className={sectionClass} aria-labelledby="conflicts-heading">
        <h2 id="conflicts-heading" className="text-xl font-semibold">
          Judge conflicts
        </h2>
        <Link className="mt-3 inline-flex min-h-11 items-center font-semibold underline" to={`/admin/mentor-review${query}`}>Review PI/lab relationships and upload mentor decisions</Link>
        <p className="mt-2 max-w-[70ch] text-sm leading-6 text-gray-600">
          Record conflicts supplied by organizers. Recording a conflict removes
          the assignment and excludes that judge’s existing scores from totals
          while retaining them in history.
        </p>
        <form
          className="mt-4 grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await apiFetch(`/competition/${event.Event_ID}/conflicts`, {
                method: 'POST',
                body: JSON.stringify({
                  Judge_ID: conflictJudge,
                  Project_ID: conflictProject,
                  Reason: reason,
                }),
              });
              setReason('');
              setNotice(
                'Conflict recorded. Any existing assignment was removed.',
              );
            });
          }}
        >
          <label className="text-sm font-semibold">
            Judge
            <select
              required
              className={fieldClass}
              value={conflictJudge}
              onChange={(e) => setConflictJudge(e.target.value)}
            >
              <option value="">Choose a judge</option>
              {judges
                .filter((j) => j.Is_Active)
                .map((j) => (
                  <option key={j.Judge_ID} value={j.Judge_ID}>
                    {j.First_Name} {j.Last_Name}
                  </option>
                ))}
            </select>
          </label>
          <label className="text-sm font-semibold">
            Presentation
            <select
              required
              className={fieldClass}
              value={conflictProject}
              onChange={(e) => setConflictProject(e.target.value)}
            >
              <option value="">Choose a presentation</option>
              {projects
                .filter((p) => p.Is_Active)
                .map((p) => (
                  <option key={p.Project_ID} value={p.Project_ID}>
                    {p.Project_Number}:{' '}
                    {p.Presenter_Display_Name ||
                      `${p.Presenter_First_Name} ${p.Presenter_Last_Name}`}
                  </option>
                ))}
            </select>
          </label>
          <label className="text-sm font-semibold sm:col-span-2">
            Reason
            <input
              required
              maxLength={500}
              className={fieldClass}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <button
            disabled={busy || !conflictJudge || !conflictProject}
            className={`${actionClass} justify-self-start`}
          >
            Record conflict
          </button>
        </form>
        {conflicts.length ? (
          <ul className="mt-5 divide-y divide-gray-200">
            {conflicts.map((conflict) => (
              <li
                key={conflict.Conflict_ID}
                className="flex flex-wrap items-center justify-between gap-3 py-4"
              >
                <div>
                  <p className="font-semibold">
                    {conflict.Judge_Name} · {conflict.Project_Number}
                  </p>
                  <p className="mt-1 text-sm">{conflict.Reason}</p>
                </div>
                <button
                  className={actionClass}
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      await apiFetch(
                        `/competition/${event.Event_ID}/conflicts/${conflict.Conflict_ID}`,
                        { method: 'DELETE' },
                      );
                      setNotice(
                        'Conflict removed. Assignments are not restored automatically; retained scores may count again.',
                      );
                    })
                  }
                >
                  Remove conflict
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-5 text-sm text-gray-600">
            No conflicts recorded. This does not confirm that no conflicts
            exist.
          </p>
        )}
      </section>
    </div>
  );
}
