import { AttendeeChoiceReport } from '../../components/admin/AttendeeChoiceReport';
import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { apiFetch } from '../../api/client';
import { getSelectedEvent } from '../../api/event';
import { downloadAdmin } from '../../api/voting';
import type { Event, Project } from '../../types';
import type {
  Voter,
  VotingRound,
  VotingSummary,
} from '../../types/competition';
import {
  actionClass,
  fieldClass,
  sectionClass,
  boolValue,
  nullableBool,
} from '../../utils/competitionUi';

interface Issued {
  voter: Voter;
  access_code: string;
}
const localTime = (value: string | null) => {
  if (!value) return '';
  const d = new Date(value);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
};
const isoTime = (value: string) =>
  value ? new Date(value).toISOString() : null;

function AffiliationEditor({
  voter,
  projects,
  busy,
  save,
}: {
  voter: Voter;
  projects: Project[];
  busy: boolean;
  save: (id: string, confirmed: boolean, ids: string[]) => void;
}) {
  const [ids, setIds] = useState(voter.Presenter_Project_IDs);
  const [confirmed, setConfirmed] = useState(voter.Affiliation_Confirmed);
  return (
    <details className="mt-3">
      <summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold">
        Confirm or correct presenter affiliation
      </summary>
      <p className="my-2 text-sm">
        Select every poster this attendee presents. Leave all unselected for a
        non-presenter.
      </p>
      <div className="max-h-56 overflow-y-auto border border-gray-300 p-3">
        {projects
          .filter((p) => p.Category === 'Poster')
          .map((p) => (
            <label
              key={p.Project_ID}
              className="flex min-h-11 items-center gap-3 text-sm"
            >
              <input
                type="checkbox"
                checked={ids.includes(p.Project_ID)}
                onChange={(e) =>
                  setIds((current) =>
                    e.target.checked
                      ? [...current, p.Project_ID]
                      : current.filter((id) => id !== p.Project_ID),
                  )
                }
              />
              {p.Project_Number}:{' '}
              {p.Presenter_Display_Name ||
                `${p.Presenter_First_Name} ${p.Presenter_Last_Name}`}
            </label>
          ))}
      </div>
      <label className="mt-3 flex min-h-11 items-center gap-3 text-sm">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        Registration staff confirmed this attendee’s affiliation
      </label>
      <button
        disabled={busy}
        className={actionClass}
        onClick={() => save(voter.Voter_ID, confirmed, ids)}
      >
        Save affiliation
      </button>
    </details>
  );
}

export function VotingPage() {
  const [params] = useSearchParams();
  const eventId = params.get('event_id');
  const [event, setEvent] = useState<Event | null>(null);
  const [rounds, setRounds] = useState<VotingRound[]>([]);
  const [selected, setSelected] = useState('');
  const [draft, setDraft] = useState<VotingRound | null>(null);
  const [summaryData, setSummary] = useState<VotingSummary | null>(null);
  const summary = summaryData?.Round_ID === selected ? summaryData : null;
  const [voters, setVoters] = useState<Voter[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [references, setReferences] = useState('');
  const [roundName, setRoundName] = useState('');
  const [printCodes, setPrintCodes] = useState(false);
  const [issued, setIssued] = useState<Issued[]>([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    const ev = await getSelectedEvent(eventId);
    setEvent(ev);
    if (!ev) return;
    const [nextRounds, nextVoters, nextProjects] = await Promise.all([
      apiFetch<VotingRound[]>(`/voting/admin/rounds?event_id=${ev.Event_ID}`),
      apiFetch<Voter[]>(`/voting/admin/voters?event_id=${ev.Event_ID}`),
      apiFetch<Project[]>(`/projects/?event_id=${ev.Event_ID}`),
    ]);
    setRounds(nextRounds);
    setVoters(nextVoters);
    setProjects(nextProjects);
    setSelected((current) =>
      nextRounds.some((r) => r.Round_ID === current)
        ? current
        : nextRounds[0]?.Round_ID || '',
    );
  }, [eventId]);
  useEffect(() => {
    setLoading(true);
    setIssued([]);
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [load]);
  useEffect(() => {
    const next = rounds.find((r) => r.Round_ID === selected);
    setDraft(next || null);
  }, [rounds, selected]);
  const loadSummary = useCallback(async () => {
    if (selected)
      setSummary(
        await apiFetch<VotingSummary>(
          `/voting/admin/rounds/${selected}/summary`,
        ),
      );
  }, [selected]);
  useEffect(() => {
    setSummary(null);
    loadSummary().catch((err) => setError(err.message));
    const timer = setInterval(
      () => loadSummary().catch((err) => setError(err.message)),
      10000,
    );
    return () => clearInterval(timer);
  }, [loadSummary]);
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      await load();
      await loadSummary();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The action failed.');
    } finally {
      setBusy(false);
    }
  }
  function downloadCodes() {
    const quote = (value: string) =>
      `"${(value.match(/^[=+@-]/) ? `'${value}` : value).replaceAll('"', '""')}"`;
    const csv = [
      'Registration reference,Voting code,Voting URL',
      ...issued.map((item) =>
        [
          item.voter.Registration_Reference,
          item.access_code,
          `${window.location.origin}/vote`,
        ]
          .map(quote)
          .join(','),
      ),
    ].join('\r\n');
    const url = URL.createObjectURL(
      new Blob([csv], { type: 'text/csv;charset=utf-8' }),
    );
    const a = document.createElement('a');
    a.href = url;
    a.download = 'new-voting-codes.csv';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (loading) return <p role="status">Loading attendee voting…</p>;
  if (!event) return <p role="alert">{error || 'No event is available.'}</p>;
  if (printCodes)
    return (
      <div>
        <div className="mb-5 flex gap-3 print:hidden">
          <button className={actionClass} onClick={() => setPrintCodes(false)}>
            Back to voting
          </button>
          <button className={actionClass} onClick={() => window.print()}>
            Print codes
          </button>
        </div>
        <h1 className="mb-5 text-xl font-semibold">
          {event.Event_Name} — voting codes
        </h1>
        <div className="grid gap-5 sm:grid-cols-2">
          {issued.map((item) => (
            <section
              key={item.voter.Voter_ID}
              className="break-inside-avoid rounded-lg border border-gray-400 bg-white p-5"
            >
              <h2 className="font-semibold">
                {item.voter.Registration_Reference}
              </h2>
              <p className="my-4 font-mono text-2xl font-bold tracking-wider">
                {item.access_code}
              </p>
              <QRCodeSVG
                size={100}
                value={`${window.location.origin}/vote`}
                title="Open attendee voting"
              />
              <p className="mt-3 break-all text-sm">
                {window.location.origin}/vote
              </p>
              <p className="mt-2 text-sm">
                Keep this code private. One code per eligible registration.
              </p>
            </section>
          ))}
        </div>
      </div>
    );
  const query = `?event_id=${encodeURIComponent(event.Event_ID)}`;
  return (
    <div>
      <h1 className="text-2xl font-bold">Attendee voting</h1>
      <p className="mt-2 text-sm text-gray-600">{event.Event_Name}</p>
      <Link className={`${actionClass} mt-4`} to={`/admin/competition${query}`}>
        Competition setup and event selection
      </Link>
      {error && (
        <p
          role="alert"
          className="my-4 border border-red-300 bg-red-50 p-4 text-red-800"
        >
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="my-4 border border-gray-300 p-4">
          {notice}
        </p>
      )}
      <section className={sectionClass}>
        <h2 className="text-xl font-semibold">Ballot access</h2>
        <div className="mt-4 flex flex-wrap items-center gap-6">
          <QRCodeSVG
            value={`${window.location.origin}/vote`}
            size={132}
            title="Attendee voting link"
          />
          <div>
            <a
              className="font-semibold underline"
              href="/vote"
              target="_blank"
              rel="noreferrer"
            >
              {window.location.origin}/vote
            </a>
            <p className="mt-3 max-w-xl text-sm leading-6">
              Each eligible registration receives one code. Replacing a lost
              code preserves its ballots and invalidates the old code and
              sessions. Registration references must uniquely identify people;
              eligibility and distribution policy still need organizer
              confirmation.
            </p>
          </div>
        </div>
      </section>
      <section className={sectionClass}>
        <h2 className="text-xl font-semibold">Voting rounds</h2>
        <label className="mt-4 block text-sm font-semibold">
          Round
          <select
            className={fieldClass}
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Choose a round</option>
            {rounds.map((r) => (
              <option key={r.Round_ID} value={r.Round_ID}>
                {r.Round_Name} ({r.Status})
              </option>
            ))}
          </select>
        </label>
        <form
          className="mt-4 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              const next = await apiFetch<VotingRound>('/voting/admin/rounds', {
                method: 'POST',
                body: JSON.stringify({
                  Event_ID: event.Event_ID,
                  Round_Name: roundName,
                }),
              });
              setSelected(next.Round_ID);
              setRoundName('');
              setNotice(
                'Draft round created. All rule choices remain pending.',
              );
            });
          }}
        >
          <label className="flex-1 text-sm font-semibold">
            New round name
            <input
              required
              maxLength={200}
              className={fieldClass}
              value={roundName}
              onChange={(e) => setRoundName(e.target.value)}
              placeholder="Name supplied by organizers"
            />
          </label>
          <button disabled={busy} className={actionClass}>
            Create draft round
          </button>
        </form>
      </section>
      {draft && (
        <>
          <form
            className={sectionClass}
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                const rules = {
                  Round_Name: draft.Round_Name,
                  Min_Choices: draft.Min_Choices,
                  Max_Choices: draft.Max_Choices,
                  Ranked: draft.Ranked,
                  Allow_Self_Votes: draft.Allow_Self_Votes,
                  Allow_Edits: draft.Allow_Edits,
                  Opens_At: draft.Opens_At,
                  Closes_At: draft.Closes_At,
                  Rules_Confirmed: draft.Rules_Confirmed,
                };
                await apiFetch(`/voting/admin/rounds/${selected}`, {
                  method: 'PUT',
                  body: JSON.stringify(rules),
                });
                setNotice(
                  'Draft rules saved. Opening the round remains a separate action.',
                );
              });
            }}
          >
            <h2 className="text-xl font-semibold">Round rules</h2>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              All choices and the schedule require confirmation. Rules freeze
              when the round is opened. Times below use your local timezone.
              Ranked ballots store order and report rank counts; an award
              weighting formula has not been chosen.
            </p>
            <fieldset
              disabled={busy || draft.Status !== 'draft'}
              className="mt-5 grid gap-5 sm:grid-cols-2"
            >
              <label className="text-sm font-semibold sm:col-span-2">
                Round name
                <input
                  className={fieldClass}
                  required
                  maxLength={200}
                  value={draft.Round_Name}
                  onChange={(e) =>
                    setDraft({ ...draft, Round_Name: e.target.value })
                  }
                />
              </label>
              {(['Min_Choices', 'Max_Choices'] as const).map((key, i) => (
                <label className="text-sm font-semibold" key={key}>
                  {i ? 'Maximum choices' : 'Minimum choices'}
                  <input
                    className={fieldClass}
                    type="number"
                    min="1"
                    max="100"
                    placeholder="Pending"
                    value={draft[key] ?? ''}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        [key]: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                  />
                </label>
              ))}
              {(
                [
                  ['Ranked', 'Are choices ranked?'],
                  [
                    'Allow_Self_Votes',
                    'May presenters vote for their own poster?',
                  ],
                  ['Allow_Edits', 'May attendees change saved ballots?'],
                ] as const
              ).map(([key, label]) => (
                <label className="text-sm font-semibold" key={key}>
                  {label}
                  <select
                    className={fieldClass}
                    value={boolValue(draft[key])}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        [key]: nullableBool(e.target.value),
                      })
                    }
                  >
                    <option value="">Pending confirmation</option>
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                </label>
              ))}
              {(['Opens_At', 'Closes_At'] as const).map((key, i) => (
                <label className="text-sm font-semibold" key={key}>
                  {i ? 'Closes at (local time)' : 'Opens at (local time)'}
                  <input
                    type="datetime-local"
                    className={fieldClass}
                    value={localTime(draft[key])}
                    onChange={(e) =>
                      setDraft({ ...draft, [key]: isoTime(e.target.value) })
                    }
                  />
                </label>
              ))}
              <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2">
                <input
                  type="checkbox"
                  checked={draft.Rules_Confirmed}
                  onChange={(e) =>
                    setDraft({ ...draft, Rules_Confirmed: e.target.checked })
                  }
                />
                Organizer confirmed these voting rules
              </label>
              <button className={`${actionClass} justify-self-start`}>
                Save draft rules
              </button>
            </fieldset>
          </form>
          <section className={sectionClass}>
            <h2 className="text-xl font-semibold">
              {summary?.Voting_Open
                ? 'Voting is open now'
                : `Round status: ${draft.Status}`}
            </h2>
            <p className="mt-3 text-sm">
              {summary?.Ballots_Submitted ?? '…'} saved ballots · refreshed
              every 10 seconds
            </p>
            {draft.Status === 'draft' &&
              summary &&
              summary.missing.length > 0 && (
                <>
                  <p className="mt-4 text-sm font-semibold">
                    Still needed before opening:
                  </p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                    {summary.missing.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                className={actionClass}
                disabled={
                  busy ||
                  draft.Status !== 'draft' ||
                  !summary ||
                  summary.missing.length > 0
                }
                onClick={() =>
                  run(async () => {
                    await apiFetch(`/voting/admin/rounds/${selected}/open`, {
                      method: 'POST',
                    });
                    setNotice(
                      'Round opened. The server enforces its scheduled window.',
                    );
                  })
                }
              >
                Open round
              </button>
              <button
                className={actionClass}
                disabled={busy || draft.Status !== 'open'}
                onClick={() => {
                  if (
                    window.confirm(
                      'Close this voting round now? Closed rounds cannot be reopened.',
                    )
                  )
                    run(async () => {
                      await apiFetch(`/voting/admin/rounds/${selected}/close`, {
                        method: 'POST',
                      });
                      setNotice(
                        'Voting round closed. Vote totals are available.',
                      );
                    });
                }}
              >
                Close round
              </button>
            </div>
            {summary?.Tallies_Available ? (
              <>
                {summary.Top_Ten_Report && <AttendeeChoiceReport
                  report={summary.Top_Ten_Report}
                  busy={busy}
                  download={() => { void run(() => downloadAdmin(
                    `/voting/admin/rounds/${selected}/top-ten/export`,
                    `attendee-choice-top-ten-${selected}.csv`,
                  )); }}
                />}
                <details className="mt-6 border-t border-gray-300 pt-3">
                <summary className="min-h-11 cursor-pointer py-3 text-lg font-semibold">Review complete tally ({summary.tally.length} posters)</summary>
                <p className="mt-2 text-sm text-gray-600">
                  Includes currently active, eligible posters only. Ranked
                  choices show their rank counts without an invented weighting
                  or automatic winner.
                </p>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr>
                        {['Poster', 'Presenter', 'Title', 'Votes', 'Rank counts'].map(
                          (label) => (
                            <th
                              className="border-b border-gray-300 px-3 py-3"
                              key={label}
                            >
                              {label}
                            </th>
                          ),
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {summary.tally.map((item) => (
                        <tr key={item.Project_Number}>
                          <td className="border-b border-gray-200 px-3 py-3 font-mono">
                            {item.Project_Number}
                          </td>
                          <td className="border-b border-gray-200 px-3 py-3">
                            {item.Presenter_Display_Name}
                          </td>
                          <td className="border-b border-gray-200 px-3 py-3">
                            {item.Project_Title}
                          </td>
                          <td className="border-b border-gray-200 px-3 py-3">
                            {item.Votes}
                          </td>
                          <td className="border-b border-gray-200 px-3 py-3">
                            {Object.entries(item.Rank_Counts)
                              .map(([rank, count]) => `#${rank}: ${count}`)
                              .join(', ') || 'Unranked'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button
                  className={`${actionClass} mt-4`}
                  disabled={busy}
                  onClick={() =>
                    run(() =>
                      downloadAdmin(
                        `/voting/admin/rounds/${selected}/export`,
                        'attendee-votes.csv',
                      ),
                    )
                  }
                >
                  Download complete vote totals
                </button>
                </details>
              </>
            ) : (
              <p className="mt-5 text-sm text-gray-600">
                Vote totals remain hidden until the round closes.
              </p>
            )}
          </section>
        </>
      )}
      <section className={sectionClass}>
        <h2 className="text-xl font-semibold">Issue voting codes</h2>
        <p className="mt-2 max-w-[75ch] text-sm leading-6 text-gray-600">
          Enter one organizer-approved registration reference per line. Codes
          are displayed once. New registrations start with affiliation
          unconfirmed; confirm each presenter or non-presenter below before a
          round that excludes self votes.
        </p>
        <form
          className="mt-4"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              const results = await apiFetch<Issued[]>(
                '/voting/admin/voters/bulk',
                {
                  method: 'POST',
                  body: JSON.stringify({
                    Event_ID: event.Event_ID,
                    Registration_References: references
                      .split('\n')
                      .map((v) => v.trim())
                      .filter(Boolean),
                  }),
                },
              );
              setIssued((current) => [...current, ...results]);
              setReferences('');
              setNotice(
                'Codes issued. Download them before leaving this page.',
              );
            });
          }}
        >
          <label className="block text-sm font-semibold">
            Unique registration references
            <textarea
              required
              rows={4}
              className={fieldClass}
              value={references}
              onChange={(e) => setReferences(e.target.value)}
            />
          </label>
          <button
            className={`${actionClass} mt-4`}
            disabled={busy || !references.trim()}
          >
            Issue codes
          </button>
        </form>
        {issued.length > 0 && (
          <div className="mt-5 border-t border-gray-300 pt-5">
            <h3 className="font-semibold">New codes — save before leaving</h3>
            <button className={`${actionClass} mt-3`} onClick={downloadCodes}>
              Download new codes
            </button>
            <button
              className={`${actionClass} ml-3 mt-3`}
              onClick={() => setPrintCodes(true)}
            >
              Print new codes
            </button>
            <ul className="mt-3 divide-y divide-gray-200">
              {issued.map((item, i) => (
                <li
                  className="flex flex-wrap justify-between gap-3 py-3 text-sm"
                  key={`${item.voter.Voter_ID}-${i}`}
                >
                  <span>{item.voter.Registration_Reference}</span>
                  <code className="select-all font-mono font-bold">
                    {item.access_code}
                  </code>
                </li>
              ))}
            </ul>
            <button
              className={`${actionClass} mt-3`}
              onClick={() => setIssued([])}
            >
              Hide saved codes
            </button>
          </div>
        )}
      </section>
      <section className={sectionClass}>
        <h2 className="text-xl font-semibold">
          Registrations ({voters.length})
        </h2>
        {voters.length === 0 && (
          <p className="mt-3 text-sm">
            No voting entitlements have been issued.
          </p>
        )}
        <ul className="mt-4 divide-y divide-gray-300">
          {voters.map((voter) => (
            <li className="py-5" key={voter.Voter_ID}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold">
                    {voter.Registration_Reference}
                  </p>
                  <p className="mt-1 text-sm text-gray-600">
                    {voter.Is_Active ? 'Active code' : 'Revoked'} ·{' '}
                    {voter.Affiliation_Confirmed
                      ? 'Affiliation confirmed'
                      : 'Affiliation pending'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    className={actionClass}
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(
                          'Replace this code and invalidate its existing sessions? Saved ballots will be retained.',
                        )
                      )
                        run(async () => {
                          const next = await apiFetch<{ access_code: string }>(
                            `/voting/admin/voters/${voter.Voter_ID}/replace-code`,
                            { method: 'POST' },
                          );
                          setIssued((current) => [
                            ...current.filter(
                              (item) => item.voter.Voter_ID !== voter.Voter_ID,
                            ),
                            { voter, access_code: next.access_code },
                          ]);
                          setNotice(
                            'Replacement code issued. Old code and sessions are invalid.',
                          );
                        });
                    }}
                  >
                    Replace code
                  </button>
                  <button
                    className={actionClass}
                    disabled={busy || !voter.Is_Active}
                    onClick={() => {
                      if (
                        window.confirm(
                          'Revoke this voting code? Saved ballots remain in history.',
                        )
                      )
                        run(async () => {
                          await apiFetch(
                            `/voting/admin/voters/${voter.Voter_ID}/revoke`,
                            { method: 'POST' },
                          );
                          setNotice('Code revoked. Saved ballots retained.');
                        });
                    }}
                  >
                    Revoke
                  </button>
                </div>
              </div>
              <AffiliationEditor
                voter={voter}
                projects={projects}
                busy={busy}
                save={(id, confirmed, ids) =>
                  run(async () => {
                    await apiFetch(`/voting/admin/voters/${id}`, {
                      method: 'PUT',
                      body: JSON.stringify({
                        Affiliation_Confirmed: confirmed,
                        Presenter_Project_IDs: ids,
                      }),
                    });
                    setNotice('Presenter affiliation saved.');
                  })
                }
              />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
