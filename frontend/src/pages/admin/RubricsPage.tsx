import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { getSelectedEvent } from '../../api/event';
import type { Criterion, Event, Rubric } from '../../types';
import {
  actionClass,
  fieldClass,
  sectionClass,
} from '../../utils/competitionUi';

type CriterionDraft = Pick<
  Criterion,
  | 'Criterion_Name'
  | 'Criterion_Group'
  | 'Description'
  | 'Min_Score'
  | 'Max_Score'
  | 'Sort_Order'
>;
const blankCriterion = (): CriterionDraft => ({
  Criterion_Name: '',
  Criterion_Group: '',
  Description: '',
  Min_Score: 0,
  Max_Score: 3,
  Sort_Order: 0,
});

export function RubricsPage() {
  const [params] = useSearchParams();
  const eventId = params.get('event_id');
  const [event, setEvent] = useState<Event | null>(null);
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [drafts, setDrafts] = useState<Record<number, CriterionDraft>>({});
  const [newCriteria, setNewCriteria] = useState<
    Record<string, CriterionDraft>
  >({});
  const [name, setName] = useState('');
  const [category, setCategory] = useState('Poster');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const load = useCallback(async () => {
    const ev = await getSelectedEvent(eventId);
    setEvent(ev);
    const data = ev
      ? await apiFetch<Rubric[]>(`/rubrics/?event_id=${ev.Event_ID}`)
      : [];
    setRubrics(data);
    setDrafts(
      Object.fromEntries(
        data.flatMap((r) =>
          r.criteria.map((c) => [
            c.Criterion_ID,
            {
              Criterion_Name: c.Criterion_Name,
              Criterion_Group: c.Criterion_Group,
              Description: c.Description,
              Min_Score: c.Min_Score,
              Max_Score: c.Max_Score,
              Sort_Order: c.Sort_Order,
            },
          ]),
        ),
      ),
    );
    setNewCriteria(
      Object.fromEntries(
        data.map((r) => [
          r.Rubric_ID,
          { ...blankCriterion(), Sort_Order: r.criteria.length },
        ]),
      ),
    );
  }, [eventId]);
  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [load]);
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save rubric.');
    } finally {
      setBusy(false);
    }
  }
  const fields = (
    draft: CriterionDraft,
    update: (draft: CriterionDraft) => void,
    disabled: boolean,
  ) => (
    <fieldset disabled={disabled} className="grid gap-3 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        Criterion name
        <input
          required
          maxLength={200}
          className={fieldClass}
          value={draft.Criterion_Name}
          onChange={(e) => update({ ...draft, Criterion_Name: e.target.value })}
        />
      </label>
      <label className="text-sm font-semibold">
        Section / group
        <input
          maxLength={100}
          className={fieldClass}
          value={draft.Criterion_Group || ''}
          onChange={(e) =>
            update({ ...draft, Criterion_Group: e.target.value || null })
          }
        />
      </label>
      <label className="text-sm font-semibold sm:col-span-2">
        Description
        <textarea
          className={fieldClass}
          rows={2}
          value={draft.Description || ''}
          onChange={(e) =>
            update({ ...draft, Description: e.target.value || null })
          }
        />
      </label>
      <label className="text-sm font-semibold">
        Minimum score
        <input
          required
          type="number"
          min={0}
          max={4}
          className={fieldClass}
          value={draft.Min_Score}
          onChange={(e) =>
            update({ ...draft, Min_Score: Number(e.target.value) })
          }
        />
      </label>
      <label className="text-sm font-semibold">
        Maximum score
        <input
          required
          type="number"
          min={1}
          max={5}
          className={fieldClass}
          value={draft.Max_Score}
          onChange={(e) =>
            update({ ...draft, Max_Score: Number(e.target.value) })
          }
        />
      </label>
      <label className="text-sm font-semibold">
        Display order
        <input
          required
          type="number"
          min={0}
          className={fieldClass}
          value={draft.Sort_Order}
          onChange={(e) =>
            update({ ...draft, Sort_Order: Number(e.target.value) })
          }
        />
      </label>
    </fieldset>
  );
  if (loading) return <p role="status">Loading rubrics…</p>;
  return (
    <div>
      <h1 className="text-2xl font-bold">Rubric setup</h1>
      <p className="mt-2 text-sm text-gray-600">
        {event?.Event_Name || 'No selected event'}
      </p>
      <p className="mt-3 max-w-[70ch] text-sm leading-6">
        Add the organizer’s approved criteria, then confirm and lock the rubric
        before opening judging. A rubric with scores cannot be changed. The
        supported scores are integers within 0–5. Each criterion keeps its own
        minimum and maximum; existing 0–3 rubrics keep their original limits.
      </p>
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
      {rubrics.map((rubric) => (
        <section key={rubric.Rubric_ID} className={`mt-5 ${sectionClass}`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">{rubric.Rubric_Name}</h2>
              <p className="mt-2 text-sm">
                {rubric.Category} · {rubric.criteria.length} criteria · maximum{' '}
                {rubric.Max_Score} points ·{' '}
                {rubric.Is_Locked
                  ? 'Confirmed and locked'
                  : 'Draft, awaiting confirmation'}
              </p>
            </div>
            <button
              className={actionClass}
              disabled={
                busy || (!rubric.Is_Locked && rubric.criteria.length === 0)
              }
              onClick={() =>
                run(async () => {
                  await apiFetch(
                    `/rubrics/${rubric.Rubric_ID}/${rubric.Is_Locked ? 'unlock' : 'lock'}`,
                    { method: 'POST' },
                  );
                  setNotice(
                    rubric.Is_Locked
                      ? 'Unscored rubric unlocked for editing.'
                      : 'Rubric confirmed and locked.',
                  );
                })
              }
            >
              {rubric.Is_Locked
                ? 'Unlock unscored rubric'
                : 'Confirm and lock rubric'}
            </button>
          </div>
          {rubric.Description && <p className="mt-4 text-sm leading-6">{rubric.Description}</p>}
          {rubric.Score_Labels && (
            <p className="mt-3 text-sm leading-6">
              {Object.entries(rubric.Score_Labels).map(([score, label]) => `${score} ${label}`).join(' · ')}
            </p>
          )}
          {rubric.criteria.map((criterion) => (
            <form
              key={criterion.Criterion_ID}
              className="mt-5 border-t border-gray-200 py-5"
              onSubmit={(e) => {
                e.preventDefault();
                run(async () => {
                  await apiFetch(
                    `/rubrics/criteria/${criterion.Criterion_ID}`,
                    {
                      method: 'PATCH',
                      body: JSON.stringify(drafts[criterion.Criterion_ID]),
                    },
                  );
                  setNotice('Criterion saved.');
                });
              }}
            >
              <h3 className="mb-4 font-semibold">{criterion.Criterion_Name}</h3>
              {drafts[criterion.Criterion_ID] &&
                fields(
                  drafts[criterion.Criterion_ID],
                  (value) =>
                    setDrafts({ ...drafts, [criterion.Criterion_ID]: value }),
                  busy || rubric.Is_Locked,
                )}
              {!rubric.Is_Locked && (
                <div className="mt-4 flex gap-2">
                  <button className={actionClass} disabled={busy}>
                    Save criterion
                  </button>
                  <button
                    type="button"
                    className={actionClass}
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        await apiFetch(
                          `/rubrics/criteria/${criterion.Criterion_ID}`,
                          { method: 'DELETE' },
                        );
                        setNotice('Unscored draft criterion removed.');
                      })
                    }
                  >
                    Remove criterion
                  </button>
                </div>
              )}
            </form>
          ))}
          {!rubric.Is_Locked && newCriteria[rubric.Rubric_ID] && (
            <form
              className="mt-5 border-t border-gray-300 py-5"
              onSubmit={(e) => {
                e.preventDefault();
                run(async () => {
                  await apiFetch(`/rubrics/${rubric.Rubric_ID}/criteria`, {
                    method: 'POST',
                    body: JSON.stringify(newCriteria[rubric.Rubric_ID]),
                  });
                  setNotice('Draft criterion added.');
                });
              }}
            >
              <h3 className="mb-4 font-semibold">Add a criterion</h3>
              {fields(
                newCriteria[rubric.Rubric_ID],
                (value) =>
                  setNewCriteria({ ...newCriteria, [rubric.Rubric_ID]: value }),
                busy,
              )}
              <button disabled={busy} className={`${actionClass} mt-4`}>
                Add draft criterion
              </button>
            </form>
          )}
        </section>
      ))}
      {event && (
        <form
          className={sectionClass}
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await apiFetch('/rubrics/', {
                method: 'POST',
                body: JSON.stringify({
                  Event_ID: event.Event_ID,
                  Rubric_Name: name.trim(),
                  Category: category,
                }),
              });
              setName('');
              setNotice('Empty draft rubric created.');
            });
          }}
        >
          <h2 className="text-xl font-semibold">Create a draft rubric</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold">
              Rubric name
              <input
                required
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={fieldClass}
              />
            </label>
            <label className="text-sm font-semibold">
              Presentation category
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className={fieldClass}
              >
                <option>Poster</option>
                <option>Art</option>
              </select>
            </label>
          </div>
          <button disabled={busy} className={`${actionClass} mt-4`}>
            Create draft rubric
          </button>
        </form>
      )}
    </div>
  );
}
