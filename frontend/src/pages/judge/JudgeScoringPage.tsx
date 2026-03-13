import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import type { JudgeProjectDetail, Criterion } from '../../types';

const SCORE_LABELS = ['Poor', 'Fair', 'Good', 'Excellent'];
const SCORE_COLORS = [
  'bg-red-100 text-red-700 border-red-300',
  'bg-orange-100 text-orange-700 border-orange-300',
  'bg-yellow-100 text-yellow-700 border-yellow-300',
  'bg-green-100 text-green-700 border-green-300',
];
const SCORE_SELECTED = [
  'bg-red-500 text-white border-red-500',
  'bg-orange-500 text-white border-orange-500',
  'bg-yellow-500 text-white border-yellow-500',
  'bg-green-500 text-white border-green-500',
];

export function JudgeScoringPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<JudgeProjectDetail | null>(null);
  const [scores, setScores] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitNotice, setSubmitNotice] = useState<string | null>(null);

  useEffect(() => { loadData(); }, [projectId]);

  async function loadData() {
    setError(null);
    try {
      const d = await apiFetch<JudgeProjectDetail>(`/judge/projects/${projectId}`);
      setDetail(d);
      setScores(d.existing_scores || {});
      setFeedback(d.existing_feedback || '');
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Failed to load project.');
    }
    finally { setLoading(false); }
  }

  function setScore(criterionId: number, value: number) {
    setScores(prev => ({ ...prev, [criterionId]: value }));
  }

  async function handleSubmit() {
    if (!detail?.rubric) return;
    setSubmitting(true);
    setError(null);
    setSubmitNotice(null);
    try {
      const scoreEntries = Object.entries(scores).map(([cid, val]) => ({
        Criterion_ID: parseInt(cid),
        Score_Value: val,
      }));
      const response = await apiFetch<{ feedback_saved?: boolean }>(`/judge/projects/${projectId}/scores`, {
        method: 'POST',
        body: JSON.stringify({ scores: scoreEntries, feedback: feedback || null }),
      });
      if (response.feedback_saved === false) {
        setSubmitNotice('Scores were saved, but feedback could not be stored.');
      }
      setSubmitted(true);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Failed to submit scores.');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="text-center py-8 text-gray-500">Loading...</div>;
  if (!detail) return <div className="text-center py-8 text-red-500">Project not found</div>;

  // Submitted confirmation
  if (submitted) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Scores Submitted!</h2>
        <p className="text-gray-500 mb-6">{detail.Project_Title}</p>
        {submitNotice && (
          <div className="mx-auto mb-6 max-w-md rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {submitNotice}
          </div>
        )}
        <button
          onClick={() => navigate('/judge/projects')}
          className="bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 transition-colors"
        >
          Score Another Project
        </button>
      </div>
    );
  }

  const criteria = detail.rubric?.criteria || [];
  const totalScore = Object.values(scores).reduce((a, b) => a + b, 0);
  const maxScore = detail.rubric?.Max_Score || 0;
  const allScored = criteria.every(c => scores[c.Criterion_ID] !== undefined);

  // Group criteria
  const groups: Record<string, Criterion[]> = {};
  criteria.forEach(c => {
    const group = c.Criterion_Group || 'General';
    if (!groups[group]) groups[group] = [];
    groups[group].push(c);
  });

  return (
    <div className="pb-28">
      {/* Project header */}
      <button
        onClick={() => navigate('/judge/projects')}
        className="mb-3 flex items-center gap-1 text-base text-blue-600 sm:text-sm"
      >
        ← Back to projects
      </button>

      <div className="mb-5 rounded-xl border border-gray-200 bg-white p-5 sm:mb-4 sm:p-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl font-mono font-bold sm:text-lg">
            {detail.Project_Number}
          </span>
          <span className={`rounded-full px-2 py-1 text-sm font-medium sm:py-0.5 sm:text-xs ${
            detail.Category === 'Art' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
          }`}>{detail.Category}</span>
        </div>
        <h2 className="text-lg font-semibold text-gray-900 sm:text-base">
          {detail.Project_Title}
        </h2>
        <p className="text-base text-gray-500 sm:text-sm">
          {detail.Presenter_First_Name} {detail.Presenter_Last_Name}
          {detail.Department && ` — ${detail.Department}`}
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Scoring form */}
      {Object.entries(groups).map(([groupName, groupCriteria]) => (
        <div key={groupName} className="mb-4">
          {groupName !== 'General' && (
            <h3 className="mb-2 text-base font-semibold uppercase tracking-wide text-gray-500 sm:text-sm">
              {groupName}
            </h3>
          )}
          <div className="space-y-4 sm:space-y-3">
            {groupCriteria.map(c => (
              <div
                key={c.Criterion_ID}
                className="rounded-xl border border-gray-200 bg-white p-4 sm:p-4"
              >
                <p className="mb-3 text-base font-medium text-gray-800 sm:text-sm">
                  {c.Criterion_Name}
                </p>
                <div className="grid grid-cols-4 gap-2.5 sm:gap-2">
                  {[0, 1, 2, 3].map(val => (
                    <button
                      key={val}
                      onClick={() => setScore(c.Criterion_ID, val)}
                      className={`min-h-20 rounded-lg border-2 px-1 py-3 text-base font-medium transition-all sm:min-h-16 sm:text-sm ${
                        scores[c.Criterion_ID] === val
                          ? SCORE_SELECTED[val]
                          : SCORE_COLORS[val]
                      }`}
                    >
                      <div className="text-2xl font-bold leading-none sm:text-lg">
                        {val}
                      </div>
                      <div className="mt-1 text-xs opacity-75 sm:text-[10px]">
                        {SCORE_LABELS[val]}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Optional feedback */}
      <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4">
        <label className="mb-2 block text-base font-medium text-gray-700 sm:text-sm">
          Feedback for Presenter <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <textarea
          value={feedback}
          onChange={e => setFeedback(e.target.value)}
          placeholder="Any comments or suggestions for the presenter..."
          rows={3}
          className="w-full resize-none rounded-lg border border-gray-300 px-3 py-3 text-base focus:border-blue-500 focus:ring-2 focus:ring-blue-500 sm:py-2 sm:text-sm"
        />
      </div>

      {/* Fixed bottom bar */}
      <div className="fixed bottom-0 left-0 right-0 flex items-center justify-between border-t border-gray-200 bg-white px-4 py-4">
        <div>
          <span className="text-3xl font-bold text-gray-900 sm:text-2xl">
            {totalScore}
          </span>
          <span className="text-base text-gray-400 sm:text-sm"> / {maxScore}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!allScored || submitting}
          className="rounded-xl bg-blue-600 px-6 py-3.5 text-base font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50 sm:px-8 sm:py-3 sm:text-sm"
        >
          {submitting ? 'Submitting...' : 'Submit Scores'}
        </button>
      </div>
    </div>
  );
}
