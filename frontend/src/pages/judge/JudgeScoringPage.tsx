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
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => { loadData(); }, [projectId]);

  async function loadData() {
    try {
      const d = await apiFetch<JudgeProjectDetail>(`/judge/projects/${projectId}`);
      setDetail(d);
      setScores(d.existing_scores || {});
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }

  function setScore(criterionId: number, value: number) {
    setScores(prev => ({ ...prev, [criterionId]: value }));
  }

  async function handleSubmit() {
    if (!detail?.rubric) return;
    setSubmitting(true);
    try {
      const scoreEntries = Object.entries(scores).map(([cid, val]) => ({
        Criterion_ID: parseInt(cid),
        Score_Value: val,
      }));
      await apiFetch(`/judge/projects/${projectId}/scores`, {
        method: 'POST',
        body: JSON.stringify({ scores: scoreEntries }),
      });
      setSubmitted(true);
    } catch (err) {
      console.error(err);
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
    <div className="pb-24">
      {/* Project header */}
      <button
        onClick={() => navigate('/judge/projects')}
        className="text-sm text-blue-600 mb-3 flex items-center gap-1"
      >
        ← Back to projects
      </button>

      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-lg font-mono font-bold">{detail.Project_Number}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            detail.Category === 'Art' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
          }`}>{detail.Category}</span>
        </div>
        <h2 className="text-base font-semibold text-gray-900">{detail.Project_Title}</h2>
        <p className="text-sm text-gray-500">
          {detail.Presenter_First_Name} {detail.Presenter_Last_Name}
          {detail.Department && ` — ${detail.Department}`}
        </p>
      </div>

      {/* Scoring form */}
      {Object.entries(groups).map(([groupName, groupCriteria]) => (
        <div key={groupName} className="mb-4">
          {groupName !== 'General' && (
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
              {groupName}
            </h3>
          )}
          <div className="space-y-3">
            {groupCriteria.map(c => (
              <div key={c.Criterion_ID} className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-sm font-medium text-gray-800 mb-3">{c.Criterion_Name}</p>
                <div className="grid grid-cols-4 gap-2">
                  {[0, 1, 2, 3].map(val => (
                    <button
                      key={val}
                      onClick={() => setScore(c.Criterion_ID, val)}
                      className={`py-3 rounded-lg border-2 text-sm font-medium transition-all ${
                        scores[c.Criterion_ID] === val
                          ? SCORE_SELECTED[val]
                          : SCORE_COLORS[val]
                      }`}
                    >
                      <div className="text-lg font-bold">{val}</div>
                      <div className="text-[10px] opacity-75">{SCORE_LABELS[val]}</div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Fixed bottom bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-3 flex items-center justify-between">
        <div>
          <span className="text-2xl font-bold text-gray-900">{totalScore}</span>
          <span className="text-sm text-gray-400"> / {maxScore}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!allScored || submitting}
          className="bg-blue-600 text-white px-8 py-3 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Submitting...' : 'Submit Scores'}
        </button>
      </div>
    </div>
  );
}
