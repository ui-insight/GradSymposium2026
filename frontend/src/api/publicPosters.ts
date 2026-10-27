import type { PublicEvent, PublicPosterDirectory } from '../types';

export async function fetchPosterDirectory(signal?: AbortSignal): Promise<PublicPosterDirectory> {
  // Public lookup must work independently of expired admin/judge credentials.
  const response = await fetch('/api/v1/public/posters', { signal, cache: 'no-store' });
  if (!response.ok) throw new Error('The poster directory could not be loaded. Please try again.');
  return response.json();
}

export function conferenceDates(event: PublicEvent): string {
  const format = (date: string) => new Intl.DateTimeFormat('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(`${date}T12:00:00Z`));
  return event.Event_End_Date && event.Event_End_Date !== event.Event_Date
    ? `${format(event.Event_Date)} – ${format(event.Event_End_Date)}`
    : format(event.Event_Date);
}
