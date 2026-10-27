import { apiFetch } from './client';
import type { Event } from '../types';

export function getSelectedEvent(
  eventId?: string | null,
): Promise<Event | null> {
  const id =
    eventId === undefined
      ? new URLSearchParams(window.location.search).get('event_id')
      : eventId;
  return apiFetch<Event | null>(
    id ? `/events/${encodeURIComponent(id)}` : '/events/active',
  );
}
