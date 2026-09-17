// In-memory fallback for environments where window.sessionStorage throws a SecurityError
// (e.g. strict cookie/storage blocking, private browsing, sandboxed iframes)
const memoryStorage: Record<string, string> = {};

export const safeSessionStorage = {
  getItem: (key: string): string | null => {
    try {
      if (typeof window !== "undefined") {
        return window.sessionStorage.getItem(key);
      }
    } catch {
      // Storage access is denied (SecurityError)
    }
    return memoryStorage[key] ?? null;
  },

  setItem: (key: string, value: string): void => {
    try {
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(key, value);
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
        window.sessionStorage.removeItem(key);
      }
    } catch {
      // Storage access is denied (SecurityError)
    }
    delete memoryStorage[key];
  },
};
