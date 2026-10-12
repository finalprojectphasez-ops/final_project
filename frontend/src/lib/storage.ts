// In-memory fallback for environments where window.sessionStorage throws a SecurityError
// (e.g. strict cookie/storage blocking, private browsing, sandboxed iframes)
const memoryStorage: Record<string, string> = {};

export const safeSessionStorage = {
  getItem: (key: string): string | null => {
    try {
      if (typeof window !== "undefined") {
        const sessionVal = window.sessionStorage.getItem(key);
        if (sessionVal !== null) return sessionVal;
        const localVal = window.localStorage.getItem(key);
        if (localVal !== null) return localVal;
      }
    } catch {
      // Storage access is denied (SecurityError)
    }
    return memoryStorage[key] ?? null;
  },

  setItem: (key: string, value: string): void => {
    try {
      if (typeof window !== "undefined") {
        try { window.sessionStorage.setItem(key, value); } catch {}
        try { window.localStorage.setItem(key, value); } catch {}
        return;
      }
    } catch {
      // Storage access is denied (SecurityError)
    }
    memoryStorage[key] = value;
  },

  removeItem: (key: string): void => {
    try {
      if (typeof window !== "undefined") {
        try { window.sessionStorage.removeItem(key); } catch {}
        try { window.localStorage.removeItem(key); } catch {}
      }
    } catch {
      // Storage access is denied (SecurityError)
    }
    delete memoryStorage[key];
  },
};
