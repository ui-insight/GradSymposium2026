import { errorMessage } from './client';
import { storage } from '../utils/storage';

export async function voterFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = storage.getItem('voter_access_token');
  const response = await fetch(`/api/v1/voting${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!response.ok) {
    if (response.status === 401) storage.removeItem('voter_access_token');
    const error = await response.json().catch(() => ({}));
    throw new Error(
      errorMessage(error.detail, 'The request could not be completed.'),
    );
  }
  return response.json();
}

export async function downloadAdmin(path: string, filename: string) {
  const response = await fetch(`/api/v1${path}`, {
    headers: { Authorization: `Bearer ${storage.getItem('access_token')}` },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(errorMessage(error.detail, 'Download failed.'));
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
