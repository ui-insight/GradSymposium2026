export const actionClass =
  'inline-flex min-h-11 items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-700 disabled:cursor-not-allowed disabled:opacity-50';
export const fieldClass =
  'mt-2 min-h-11 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-base font-normal focus-visible:outline-2 focus-visible:outline-amber-700';
export const sectionClass = 'border-t border-gray-300 py-6';
export const nullableBool = (value: string): boolean | null =>
  value === '' ? null : value === 'true';
export const boolValue = (value: boolean | null): string =>
  value === null ? '' : String(value);
