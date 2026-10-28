import type { Rubric } from '../../types';

export function RubricHelp({ rubric }: { rubric: Rubric }) {
  return (
    <details className="mb-5 rounded-xl border border-gray-300 bg-stone-50 p-4">
      <summary className="min-h-11 cursor-pointer content-center font-semibold text-gray-900 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-700">
        Rubric help
      </summary>
      <div className="mt-3 max-w-[70ch] text-sm leading-6">
        <h3 className="font-semibold">{rubric.Rubric_Name}</h3>
        {rubric.Description && <p className="mt-2">{rubric.Description}</p>}
        {rubric.Score_Labels && (
          <dl className="mt-3 grid gap-x-6 gap-y-1 sm:grid-cols-2">
            {Object.entries(rubric.Score_Labels)
              .sort(([a], [b]) => Number(b) - Number(a))
              .map(([value, label]) => (
                <div key={value} className="flex gap-2">
                  <dt className="font-semibold">{value}</dt>
                  <dd>{label}</dd>
                </div>
              ))}
          </dl>
        )}
        <dl className="mt-4 divide-y divide-gray-200">
          {rubric.criteria.map((criterion) => (
            <div key={criterion.Criterion_ID} className="py-3">
              <dt className="font-semibold">{criterion.Criterion_Name}</dt>
              <dd>
                {criterion.Description && <p>{criterion.Description}</p>}
                <p className="text-gray-600">
                  {criterion.Min_Score}–{criterion.Max_Score} points
                </p>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </details>
  );
}
