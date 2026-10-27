import { storage } from '../utils/storage';

const BASE_URL = '/api/v1';

export function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail))
    return detail
      .map((item) => {
        if (!item || typeof item !== 'object') return fallback;
        const issue = item as { loc?: unknown[]; msg?: unknown };
        const field = issue.loc
          ?.filter((value) => value !== 'body')
          .join(' / ');
        return `${field ? `${field}: ` : ''}${typeof issue.msg === 'string' ? issue.msg : fallback}`;
      })
      .join('; ');
  return fallback;
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = storage.getItem('access_token');
  const headers: Record<string, string> = {
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!(options?.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    if (res.status === 401) {
      storage.removeItem('access_token');
      storage.removeItem('user_role');
      const currentPath = window.location.pathname;
      if (currentPath.startsWith('/judge')) {
        window.location.href = '/judge';
      } else if (currentPath.startsWith('/admin')) {
        window.location.href = '/admin/login';
      }
    }
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorMessage(error.detail, res.statusText));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
