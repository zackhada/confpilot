// localStorage can throw (private windows, blocked site data), so every access is guarded.

export function readStored(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

export function writeStored(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // The app still works for this visit; the value is simply not remembered.
  }
}

export function removeStored(key: string): void {
  try {
    window.localStorage.removeItem(key)
  } catch {
    // Nothing to remove if storage is unavailable.
  }
}

export function readStoredJson<T>(key: string, isValid: (value: unknown) => value is T): T | null {
  const raw = readStored(key)
  if (raw === null) return null
  try {
    const parsed: unknown = JSON.parse(raw)
    return isValid(parsed) ? parsed : null
  } catch {
    return null
  }
}
