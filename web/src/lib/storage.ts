// Storage can throw (private mode, blocked site data); every read and write survives that.

function safe(kind: 'local' | 'session'): Storage | null {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage
  } catch {
    return null
  }
}

export function readStored(key: string, kind: 'local' | 'session' = 'local'): string | null {
  try {
    return safe(kind)?.getItem(key) ?? null
  } catch {
    return null
  }
}

export function writeStored(key: string, value: string | null, kind: 'local' | 'session' = 'local'): void {
  try {
    const store = safe(kind)
    if (value === null) store?.removeItem(key)
    else store?.setItem(key, value)
  } catch {
    // Nothing to do: the value just won't outlive this page.
  }
}
