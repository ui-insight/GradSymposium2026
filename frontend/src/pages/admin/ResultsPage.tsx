import { useState, useEffect, useRef, useCallback } from 'react';
import { apiFetch } from '../../api/client';
import type {
  Event,
  JudgeScoreReview,
  ProjectResult,
  ProjectScoreReview,
  ProjectScoreReviewCriterion,
} from '../../types';

interface ActivityItem {
  Judge_Name: string;
  Project_Number: string;
  Project_Title: string;
  Category: string;
  Total_Score: number;
  Scored_At: string | null;
}

function buildDraftScores(review: ProjectScoreReview): Record<number, number> {
  const drafts: Record<number, number> = {};
  review.submissions.forEach(submission => {
    submission.criteria.forEach(criterion => {
      drafts[criterion.Score_ID] = criterion.Score_Value;
    });
  });
  return drafts;
}

export function ResultsPage() {
  const [results, setResults] = useState<ProjectResult[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [selectedProject, setSelectedProject] = useState<ProjectResult | null>(null);
  const [review, setReview] = useState<ProjectScoreReview | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewNotice, setReviewNotice] = useState<string | null>(null);
  const [draftScores, setDraftScores] = useState<Record<number, number>>({});
  const [savingJudgeId, setSavingJudgeId] = useState<string | null>(null);
  const eventRef = useRef<Event | null>(null);

  const loadData = useCallback(async () => {
    try {
      const ev = eventRef.current || await apiFetch<Event | null>('/events/active');
      if (!eventRef.current && ev) {
        eventRef.current = ev;
        setEvent(ev);
      }
      if (ev) {
        const [r, a] = await Promise.all([
          apiFetch<ProjectResult[]>(`/results/?event_id=${ev.Event_ID}`),
          apiFetch<ActivityItem[]>(`/results/activity?event_id=${ev.Event_ID}&limit=8`)
            .catch(err => {
              console.error('Failed to load recent activity:', err);
              return [];
            }),
        ]);
        setResults(r);
        setActivity(a);
        setLastRefresh(new Date());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  async function loadReview(project: ProjectResult) {
    setSelectedProject(project);
    setReview(null);
    setReviewLoading(true);
    setReviewError(null);
    setReviewNotice(null);

    try {
      const nextReview = await apiFetch<ProjectScoreReview>(
        `/scores/review/${project.Project_ID}`
      );
      setReview(nextReview);
      setDraftScores(buildDraftScores(nextReview));
    } catch (err) {
      console.error(err);
      setReviewError(err instanceof Error ? err.message : 'Failed to load score review.');
    } finally {
      setReviewLoading(false);
    }
  }

  async function handleExport() {
    if (!event) return;
    const token = localStorage.getItem('access_token');
    const res = await fetch(`/api/v1/results/export?event_id=${event.Event_ID}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'symposium_results.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleSaveSubmission(submission: JudgeScoreReview) {
    if (!review) return;

    const changed = submission.criteria.filter(criterion => {
      const draft = draftScores[criterion.Score_ID];
      return draft !== undefined && draft !== criterion.Score_Value;
    });
    if (changed.length === 0) return;

    setSavingJudgeId(submission.Judge_ID);
    setReviewError(null);
    setReviewNotice(null);

    try {
      await Promise.all(
        changed.map(criterion =>
          apiFetch(`/scores/${criterion.Score_ID}`, {
            method: 'PATCH',
            body: JSON.stringify({
              Score_Value: draftScores[criterion.Score_ID],
            }),
          })
        )
      );

      const refreshed = await apiFetch<ProjectScoreReview>(
        `/scores/review/${review.Project_ID}`
      );
      setReview(refreshed);
      setDraftScores(buildDraftScores(refreshed));
      setReviewNotice(
        changed.length === 1
          ? 'Saved 1 score override.'
          : `Saved ${changed.length} score overrides.`
      );
      await loadData();
    } catch (err) {
      console.error(err);
      setReviewError(err instanceof Error ? err.message : 'Failed to save score overrides.');
    } finally {
      setSavingJudgeId(null);
    }
  }

  function closeReview() {
    setSelectedProject(null);
    setReview(null);
    setReviewError(null);
    setReviewNotice(null);
    setSavingJudgeId(null);
    setDraftScores({});
  }

  function timeAgo(isoStr: string | null): string {
    if (!isoStr) return '';
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ago`;
  }

  function formatDateTime(isoStr: string | null): string {
    if (!isoStr) return 'Not available';
    return new Date(isoStr).toLocaleString();
  }

  function draftValue(criterion: ProjectScoreReviewCriterion): number {
    return draftScores[criterion.Score_ID] ?? criterion.Score_Value;
  }

  const filtered = filter
    ? results.filter(r => r.Category === filter)
    : results;

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Results</h1>
          <span className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Live
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadData}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            Refresh
          </button>
          <button
            onClick={handleExport}
            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700"
          >
            Export Excel
          </button>
        </div>
      </div>

      <p className="text-xs text-gray-400 mb-4">
        Auto-refreshes every 10s &middot; Last updated {lastRefresh.toLocaleTimeString()}
      </p>

      {activity.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Recent Scoring Activity
          </h2>
          <div className="space-y-2">
            {activity.map((a, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      a.Category === 'Art'
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {a.Project_Number}
                  </span>
                  <span className="text-gray-700 font-medium truncate">{a.Judge_Name}</span>
                  <span className="text-gray-400 hidden sm:inline">scored</span>
                  <span className="text-gray-500 truncate hidden sm:inline">
                    {a.Project_Title}
                  </span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                  <span className="font-mono font-semibold text-gray-900">
                    {a.Total_Score}
                  </span>
                  <span className="text-xs text-gray-400 w-16 text-right">
                    {timeAgo(a.Scored_At)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        {['', 'Poster', 'Art'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f || 'All'}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Rank</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">#</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Title</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Presenter</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Dept</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Type</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">Judges</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">Total</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">Avg</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">Review</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map(r => (
              <tr key={r.Project_ID} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                      r.Rank <= 3
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {r.Rank}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono">{r.Project_Number}</td>
                <td className="px-4 py-3 max-w-xs truncate">{r.Project_Title}</td>
                <td className="px-4 py-3">
                  {r.Presenter_First_Name} {r.Presenter_Last_Name}
                </td>
                <td className="px-4 py-3 text-gray-500">{r.Department || '—'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      r.Category === 'Art'
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {r.Category}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">{r.Judge_Count}</td>
                <td className="px-4 py-3 text-right font-semibold">{r.Total_Score}</td>
                <td className="px-4 py-3 text-right font-semibold text-blue-600">
                  {r.Average_Score}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => loadReview(r)}
                    className="text-sm font-medium text-blue-600 hover:text-blue-800"
                  >
                    Review Scores
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-8 text-gray-400">No scores yet</div>
        )}
      </div>

      {selectedProject && (
        <div className="fixed inset-0 z-50 flex justify-end bg-gray-900/40">
          <div className="h-full w-full max-w-4xl overflow-y-auto bg-gray-50 shadow-2xl">
            <div className="sticky top-0 z-10 border-b border-gray-200 bg-white px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-lg font-bold text-gray-900">
                      {selectedProject.Project_Number}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        selectedProject.Category === 'Art'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {selectedProject.Category}
                    </span>
                  </div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {selectedProject.Project_Title}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {selectedProject.Presenter_First_Name}{' '}
                    {selectedProject.Presenter_Last_Name}
                    {selectedProject.Department && ` • ${selectedProject.Department}`}
                  </p>
                </div>
                <button
                  onClick={closeReview}
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="px-6 py-6">
              {reviewLoading && (
                <div className="rounded-xl border border-gray-200 bg-white p-6 text-gray-500">
                  Loading score review...
                </div>
              )}

              {reviewError && (
                <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {reviewError}
                </div>
              )}

              {reviewNotice && (
                <div className="mb-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                  {reviewNotice}
                </div>
              )}

              {review && (
                <div className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-xl border border-gray-200 bg-white p-4">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                        Judges
                      </div>
                      <div className="mt-2 text-2xl font-semibold text-gray-900">
                        {review.submissions.length}
                      </div>
                    </div>
                    <div className="rounded-xl border border-gray-200 bg-white p-4">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                        Current Total
                      </div>
                      <div className="mt-2 text-2xl font-semibold text-gray-900">
                        {review.submissions.reduce(
                          (sum, submission) => sum + submission.Total_Score,
                          0
                        )}
                      </div>
                    </div>
                    <div className="rounded-xl border border-gray-200 bg-white p-4">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                        Average
                      </div>
                      <div className="mt-2 text-2xl font-semibold text-gray-900">
                        {review.submissions.length
                          ? (
                              review.submissions.reduce(
                                (sum, submission) => sum + submission.Total_Score,
                                0
                              ) / review.submissions.length
                            ).toFixed(2)
                          : '0.00'}
                      </div>
                    </div>
                  </div>

                  {review.submissions.map(submission => {
                    const changedCount = submission.criteria.filter(criterion => {
                      const draft = draftScores[criterion.Score_ID];
                      return draft !== undefined && draft !== criterion.Score_Value;
                    }).length;

                    return (
                      <section
                        key={submission.Judge_ID}
                        className="rounded-2xl border border-gray-200 bg-white p-5"
                      >
                        <div className="flex flex-col gap-3 border-b border-gray-100 pb-4 md:flex-row md:items-start md:justify-between">
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900">
                              {submission.Judge_Name}
                            </h3>
                            <p className="text-sm text-gray-500">
                              {submission.Judge_Department || 'No department listed'}
                            </p>
                            <p className="mt-1 text-xs text-gray-400">
                              Submitted {formatDateTime(submission.Submitted_At)}
                            </p>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                                Current Total
                              </div>
                              <div className="text-2xl font-semibold text-gray-900">
                                {submission.Total_Score}
                              </div>
                            </div>
                            <button
                              onClick={() => handleSaveSubmission(submission)}
                              disabled={changedCount === 0 || savingJudgeId === submission.Judge_ID}
                              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {savingJudgeId === submission.Judge_ID
                                ? 'Saving...'
                                : changedCount > 0
                                  ? `Save ${changedCount} change${changedCount > 1 ? 's' : ''}`
                                  : 'No changes'}
                            </button>
                          </div>
                        </div>

                        {submission.Feedback_Text && (
                          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                            <div className="font-medium text-amber-800 mb-1">
                              Judge Feedback
                            </div>
                            {submission.Feedback_Text}
                          </div>
                        )}

                        <div className="mt-4 overflow-x-auto">
                          <table className="w-full min-w-[760px] text-sm">
                            <thead>
                              <tr className="border-b border-gray-200 text-left text-gray-500">
                                <th className="py-2 pr-4 font-medium">Criterion</th>
                                <th className="py-2 pr-4 font-medium">Original</th>
                                <th className="py-2 pr-4 font-medium">Current</th>
                                <th className="py-2 pr-4 font-medium">Override</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {submission.criteria.map(criterion => {
                                const latestOverride = criterion.Latest_Override;
                                const value = draftValue(criterion);
                                const changed = value !== criterion.Score_Value;

                                return (
                                  <tr key={criterion.Score_ID}>
                                    <td className="py-3 pr-4 align-top">
                                      <div className="font-medium text-gray-900">
                                        {criterion.Criterion_Name}
                                      </div>
                                      {criterion.Criterion_Group && (
                                        <div className="text-xs text-gray-400 mt-1">
                                          {criterion.Criterion_Group}
                                        </div>
                                      )}
                                    </td>
                                    <td className="py-3 pr-4 align-top text-gray-700">
                                      <div className="font-mono text-base">
                                        {criterion.Original_Score_Value}
                                      </div>
                                      {criterion.Override_Count > 0 && (
                                        <div className="mt-1 text-xs text-amber-700">
                                          {criterion.Override_Count} override
                                          {criterion.Override_Count > 1 ? 's' : ''}
                                        </div>
                                      )}
                                    </td>
                                    <td className="py-3 pr-4 align-top">
                                      <div className="flex items-center gap-2">
                                        {[0, 1, 2, 3].map(score => (
                                          <button
                                            key={score}
                                            onClick={() =>
                                              setDraftScores(prev => ({
                                                ...prev,
                                                [criterion.Score_ID]: score,
                                              }))
                                            }
                                            className={`h-9 w-9 rounded-lg border text-sm font-semibold transition-colors ${
                                              value === score
                                                ? changed
                                                  ? 'border-amber-500 bg-amber-500 text-white'
                                                  : 'border-blue-600 bg-blue-600 text-white'
                                                : 'border-gray-200 bg-white text-gray-600 hover:border-blue-300'
                                            }`}
                                          >
                                            {score}
                                          </button>
                                        ))}
                                      </div>
                                      <div className="mt-1 text-xs text-gray-400">
                                        Current stored value: {criterion.Score_Value}
                                      </div>
                                    </td>
                                    <td className="py-3 pr-0 align-top text-xs text-gray-500">
                                      {latestOverride ? (
                                        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                                          <div className="font-medium text-gray-700">
                                            {latestOverride.Admin_Username} set{' '}
                                            {latestOverride.Old_Score_Value} to{' '}
                                            {latestOverride.New_Score_Value}
                                          </div>
                                          <div className="mt-1 text-gray-400">
                                            {formatDateTime(latestOverride.Overridden_At)}
                                          </div>
                                        </div>
                                      ) : (
                                        <span className="text-gray-400">
                                          No admin override
                                        </span>
                                      )}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </section>
                    );
                  })}

                  {review.submissions.length === 0 && (
                    <div className="rounded-xl border border-gray-200 bg-white p-6 text-gray-500">
                      No scored submissions found for this project.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
