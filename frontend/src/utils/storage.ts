const memoryStorage = new Map<string, string>();

function getLocalStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export const storage = {
  getItem(key: string): string | null {
    const localStorage = getLocalStorage();
    if (!localStorage) {
      return memoryStorage.get(key) ?? null;
    }

    try {
      return localStorage.getItem(key);
    } catch {
      return memoryStorage.get(key) ?? null;
    }
  },

  setItem(key: string, value: string) {
    memoryStorage.set(key, value);

    const localStorage = getLocalStorage();
    if (!localStorage) {
      return;
    }

    try {
      localStorage.setItem(key, value);
    } catch {
      // Some mobile browsers block persistent storage in private or embedded views.
    }
  },

  removeItem(key: string) {
    memoryStorage.delete(key);

    const localStorage = getLocalStorage();
    if (!localStorage) {
      return;
    }

    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore storage cleanup failures and rely on in-memory state.
    }
  },
};
