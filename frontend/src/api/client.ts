const BASE_URL = '/api/v1';

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
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
      localStorage.removeItem('access_token');
      const currentPath = window.location.pathname;
      if (currentPath.startsWith('/judge')) {
        window.location.href = '/judge';
      } else {
        window.location.href = '/admin/login';
      }
    }
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof error.detail === 'string' ? error.detail : res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
