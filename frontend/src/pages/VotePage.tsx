import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { voterFetch } from '../api/voting';
import { storage } from '../utils/storage';
import { actionClass, fieldClass, sectionClass } from '../utils/competitionUi';
import type {
  SavedBallot,
  VoterSession,
  VotingPoster,
  VotingRound,
} from '../types/competition';

const at = (value: string | null) =>
  value ? new Date(value).toLocaleString() : 'Pending';

export function VotePage() {
  const [session, setSession] = useState<VoterSession | null>(null);
  const [rounds, setRounds] = useState<VotingRound[]>([]);
  const [roundId, setRoundId] = useState('');
  const [posters, setPosters] = useState<VotingPoster[]>([]);
  const [ballot, setBallot] = useState<SavedBallot | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [code, setCode] = useState('');
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [clock, setClock] = useState(Date.now());
  const [loading, setLoading] = useState(true);

  const loadSession = useCallback(async () => {
    const next = await voterFetch<VoterSession>('/me');
    setSession(next);
    setRounds(next.rounds);
    setRoundId((current) =>
      next.rounds.some((r) => r.Round_ID === current)
        ? current
        : next.rounds[0]?.Round_ID || '',
    );
  }, []);
  useEffect(() => {
    const start = storage.getItem('voter_access_token')
      ? loadSession()
      : voterFetch<VotingRound[]>('/rounds').then(setRounds);
    start
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [loadSession]);
  const signedIn = Boolean(session);
  useEffect(() => {
    if (!signedIn || !roundId) return;
    let cancelled = false;
    setBusy(true);
    setReviewing(false);
    setError('');
    setNotice('');
    setBallot(null);
    setSelected([]);
    setPosters([]);
    Promise.all([
      voterFetch<VotingPoster[]>(`/rounds/${roundId}/posters`),
      voterFetch<SavedBallot>(`/rounds/${roundId}/ballot`),
    ])
      .then(([choices, saved]) => {
        if (!cancelled) {
          setPosters(choices);
          setBallot(saved);
          setSelected(saved.Project_IDs);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
    // A periodic session refresh must not overwrite a ballot being edited.
  }, [roundId, signedIn]);
  useEffect(() => {
    const timer = setInterval(() => {
      setClock(Date.now());
      if (storage.getItem('voter_access_token'))
        loadSession().catch((err) => setError(err.message));
    }, 15000);
    return () => clearInterval(timer);
  }, [loadSession]);

  const round = rounds.find((r) => r.Round_ID === roundId);
  const open = Boolean(
    round &&
    round.Status === 'open' &&
    round.Rules_Confirmed &&
    round.Opens_At &&
    round.Closes_At &&
    clock >= Date.parse(round.Opens_At) &&
    clock < Date.parse(round.Closes_At),
  );
  const affiliationReady =
    round?.Allow_Self_Votes === true || (round?.Candidate_Type === 'talk' ? session?.Talk_Affiliation_Confirmed : session?.Affiliation_Confirmed);
  const canEdit =
    open && ballot !== null && affiliationReady && (!ballot.saved || round?.Allow_Edits === true);
  const validSize =
    round?.Min_Choices != null &&
    round.Max_Choices != null &&
    selected.length >= round.Min_Choices &&
    selected.length <= round.Max_Choices;
  const validSelection = selected.every((id) =>
    posters.some((p) => p.Project_ID === id && p.Can_Select),
  );

  async function login() {
    setBusy(true);
    setError('');
    try {
      const result = await voterFetch<{ access_token: string }>('/login', {
        method: 'POST',
        body: JSON.stringify({ access_code: code }),
      });
      storage.setItem('voter_access_token', result.access_token);
      setCode('');
      await loadSession();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed.');
    } finally {
      setBusy(false);
    }
  }
  async function submit() {
    if (!round) return;
    setBusy(true);
    setError('');
    try {
      const saved = await voterFetch<SavedBallot>(
        `/rounds/${round.Round_ID}/ballot`,
        { method: 'POST', body: JSON.stringify({ Project_IDs: selected }) },
      );
      setBallot(saved);
      setSelected(saved.Project_IDs);
      setReviewing(false);
      setNotice('Your ballot is saved.');
      await loadSession();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Your ballot could not be saved. Your choices are still shown; try again.',
      );
    } finally {
      setBusy(false);
    }
  }
  function toggle(id: string) {
    setSelected((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
    setReviewing(false);
    setNotice('');
  }
  function move(index: number, step: number) {
    setSelected((current) => {
      const next = [...current];
      [next[index], next[index + step]] = [next[index + step], next[index]];
      return next;
    });
    setReviewing(false);
  }

  return (
    <div className="min-h-screen bg-[#f7f7f3] text-gray-900">
      <header className="border-b border-gray-300 bg-white">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3 px-5 py-5">
          <Link className="text-sm font-semibold underline" to="/">
            Conference home
          </Link>
          <Link className={actionClass} to="/posters">
            Find a poster
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 py-8">
        <h1 className="text-3xl font-bold">Attendee voting</h1>
        <p className="mt-3 text-base leading-7">
          {session?.Event_Name ||
            'Use the voting code provided by registration staff.'}
        </p>
        {session?.Is_Rehearsal && (
          <p className="mt-5 border border-amber-300 bg-amber-50 p-4 text-sm leading-6">
            Synthetic rehearsal. These fictional posters and example rules are
            for testing only.
          </p>
        )}
        {loading && (
          <p className="mt-5" role="status">
            Loading voting information…
          </p>
        )}
        {error && (
          <p
            role="alert"
            className="my-5 border border-red-300 bg-red-50 p-4 text-red-800"
          >
            {error}
          </p>
        )}
        {notice && (
          <p
            role="status"
            className="my-5 border border-green-400 bg-green-50 p-4 font-semibold"
          >
            {notice}
          </p>
        )}
        {!session ? (
          <>
            <form
              className={sectionClass}
              onSubmit={(e) => {
                e.preventDefault();
                login();
              }}
            >
              <label className="block text-sm font-semibold">
                Voting code
                <input
                  required
                  autoComplete="off"
                  autoCapitalize="characters"
                  spellCheck={false}
                  maxLength={64}
                  className={`${fieldClass} font-mono text-lg`}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              </label>
              <button
                disabled={busy || !code.trim()}
                className={`${actionClass} mt-4`}
              >
                {busy ? 'Checking code…' : 'Continue to ballot'}
              </button>
            </form>
            <section className={sectionClass}>
              <h2 className="text-lg font-semibold">Voting rounds</h2>
              {rounds.length ? (
                <ul className="mt-3 divide-y divide-gray-200">
                  {rounds.map((r) => (
                    <li key={r.Round_ID} className="py-3">
                      <p className="font-semibold">{r.Round_Name}</p>
                      <p className="mt-1 text-sm">
                        {r.Status === 'draft'
                          ? 'Rules and opening time are pending organizer confirmation.'
                          : r.Status === 'closed'
                            ? 'Closed'
                            : `Scheduled ${at(r.Opens_At)} to ${at(r.Closes_At)}`}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm">
                  No public voting round is available yet.
                </p>
              )}
            </section>
          </>
        ) : (
          <>
            <button
              className={`${actionClass} mt-4`}
              onClick={() => {
                storage.removeItem('voter_access_token');
                setSession(null);
                setRoundId('');
                setBallot(null);
                setSelected([]);
                setError('');
                setNotice('');
                voterFetch<VotingRound[]>('/rounds')
                  .then(setRounds)
                  .catch((err) => setError(err.message));
              }}
            >
              Use a different voting code
            </button>
            {rounds.length === 0 ? (
              <p className="mt-6">
                No voting rounds have been prepared for this event.
              </p>
            ) : (
              <label className="mt-6 block text-sm font-semibold">
                Voting round
                <select
                  className={fieldClass}
                  value={roundId}
                  onChange={(e) => setRoundId(e.target.value)}
                >
                  {rounds.map((r) => (
                    <option value={r.Round_ID} key={r.Round_ID}>
                      {r.Round_Name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {round && (
              <>
                <section className={sectionClass}>
                  <h2 className="text-xl font-semibold">
                    {open
                      ? 'Voting is open'
                      : round.Status === 'draft'
                        ? 'Voting rules are pending'
                        : 'Voting is closed or outside its scheduled window'}
                  </h2>
                  <p className="mt-3 text-sm leading-6">
                    {round.Min_Choices != null && round.Max_Choices != null
                      ? `Choose ${round.Min_Choices === round.Max_Choices ? round.Min_Choices : `${round.Min_Choices}–${round.Max_Choices}`} distinct presentations. `
                      : ''}
                    {round.Ranked === true
                      ? 'Rank your choices from first to last. '
                      : round.Ranked === false
                        ? 'Choices have equal weight; order does not matter. '
                        : ''}
                    {round.Allow_Edits === true
                      ? 'You may change your saved ballot while voting is open.'
                      : round.Allow_Edits === false
                        ? 'You may submit once; changes are not allowed.'
                        : ''}
                  </p>
                  <p className="mt-2 text-sm text-gray-600">
                    Opens {at(round.Opens_At)} · Closes {at(round.Closes_At)}{' '}
                    (your local time)
                  </p>
                  {!affiliationReady && (
                    <p className="mt-3 font-semibold">
                      Ask registration staff to confirm your presenter
                      affiliation before voting.
                    </p>
                  )}
                  {ballot?.saved && (
                    <p className="mt-4 font-semibold">
                      Saved {at(ballot.Updated_At || ballot.Submitted_At)}.{' '}
                      {round.Allow_Edits && open
                        ? 'Your saved choices are shown below.'
                        : 'Your saved ballot is recorded.'}
                    </p>
                  )}
                </section>
                <section className={sectionClass}>
                  <h2 className="text-xl font-semibold">
                    Your choices ({selected.length})
                  </h2>
                  {selected.length ? (
                    <ol className="mt-3 divide-y divide-gray-200">
                      {selected.map((id, index) => {
                        const p = posters.find(
                          (item) => item.Project_ID === id,
                        );
                        return (
                          <li
                            className="flex flex-wrap items-center justify-between gap-3 py-3"
                            key={id}
                          >
                            <span>
                              {round.Ranked && `${index + 1}. `}
                              <span className="font-mono font-semibold">
                                {p?.Project_Number || 'Withdrawn selection'}
                              </span>
                              {p && ` · ${p.Presenter_Display_Name}`}
                            </span>
                            {canEdit && (
                              <div className="flex gap-2">
                                {round.Ranked && (
                                  <>
                                    <button
                                      className={actionClass}
                                      aria-label={`Move choice ${index + 1} up`}
                                      disabled={index === 0 || busy}
                                      onClick={() => move(index, -1)}
                                    >
                                      Up
                                    </button>
                                    <button
                                      className={actionClass}
                                      aria-label={`Move choice ${index + 1} down`}
                                      disabled={
                                        index === selected.length - 1 || busy
                                      }
                                      onClick={() => move(index, 1)}
                                    >
                                      Down
                                    </button>
                                  </>
                                )}
                                <button
                                  className={actionClass}
                                  disabled={busy}
                                  onClick={() => toggle(id)}
                                >
                                  Remove
                                </button>
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ol>
                  ) : (
                    <p className="mt-3 text-sm">No presentations selected yet.</p>
                  )}
                  {canEdit && (
                    <div className="mt-5 border-t border-gray-200 pt-5">
                      {reviewing ? (
                        <>
                          <p className="mb-4 text-sm font-semibold">
                            Review the choices above, then confirm your ballot.
                          </p>
                          <div className="flex flex-wrap gap-3">
                            <button
                              className={actionClass}
                              disabled={busy || !validSize || !validSelection}
                              onClick={submit}
                            >
                              {busy ? 'Saving…' : 'Confirm and save ballot'}
                            </button>
                            <button
                              className={actionClass}
                              disabled={busy}
                              onClick={() => setReviewing(false)}
                            >
                              Keep choosing
                            </button>
                          </div>
                        </>
                      ) : (
                        <button
                          className={actionClass}
                          disabled={busy || !validSize || !validSelection}
                          onClick={() => setReviewing(true)}
                        >
                          Review ballot
                        </button>
                      )}
                    </div>
                  )}
                </section>
                {canEdit && (
                  <section className={sectionClass}>
                    <h2 className="text-xl font-semibold">Choose presentations</h2>
                    <label className="mt-4 block text-sm font-semibold">
                      Search by number, presenter, institution, or title
                      <input
                        type="search"
                        className={fieldClass}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </label>
                    <div className="mt-4 divide-y divide-gray-200">
                      {posters
                        .filter((p) =>
                          `${p.Project_Number} ${p.Presenter_Display_Name} ${p.Project_Title} ${p.Institution || ''}`
                            .toLowerCase()
                            .includes(search.toLowerCase()),
                        )
                        .map((p) => (
                          <label
                            key={p.Project_ID}
                            className="flex min-h-14 items-start gap-4 py-5"
                          >
                            <input
                              type="checkbox"
                              className="mt-1 h-5 w-5 shrink-0"
                              checked={selected.includes(p.Project_ID)}
                              disabled={
                                busy ||
                                !p.Can_Select ||
                                (!selected.includes(p.Project_ID) &&
                                  selected.length >= (round.Max_Choices ?? 0))
                              }
                              onChange={() => toggle(p.Project_ID)}
                            />
                            <span>
                              <span className="font-mono font-bold">
                                {p.Project_Number}
                              </span>
                              <span className="ml-3 font-semibold">
                                {p.Presenter_Display_Name}
                              </span>
                              <span className="mt-1 block text-sm leading-6">
                                {p.Project_Title}
                              </span>
                              {p.Institution && (
                                <span className="mt-1 block text-sm text-gray-600">
                                  {p.Institution}
                                </span>
                              )}
                              {!p.Can_Select && (
                                <span className="mt-1 block text-sm font-semibold">
                                  Own presentation — excluded by this round’s rules
                                </span>
                              )}
                            </span>
                          </label>
                        ))}
                    </div>
                    {!posters.length && (
                      <p className="mt-4">No eligible presentations are available.</p>
                    )}
                  </section>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
