import { useCallback, useEffect, useRef, useState } from 'react'

export interface QueryState<T> {
  data: T | undefined
  error: Error | undefined
  loading: boolean
  reload: () => void
}

/**
 * Minimal data loading for the skeleton: run `load` when `key` changes, keep
 * the last result while reloading. A shared cache (and live updates over SSE)
 * arrives with the screens that need it.
 */
export function useQuery<T>(key: string | null, load: () => Promise<T>): QueryState<T> {
  const [data, setData] = useState<T>()
  const [error, setError] = useState<Error>()
  const [loading, setLoading] = useState(key !== null)
  const [tick, setTick] = useState(0)
  const loadRef = useRef(load)
  loadRef.current = load

  useEffect(() => {
    if (key === null) return
    let live = true
    setLoading(true)
    loadRef
      .current()
      .then((value) => {
        if (!live) return
        setData(value)
        setError(undefined)
      })
      .catch((err: unknown) => {
        if (live) setError(err instanceof Error ? err : new Error(String(err)))
      })
      .finally(() => {
        if (live) setLoading(false)
      })
    return () => {
      live = false
    }
  }, [key, tick])

  const reload = useCallback(() => setTick((n) => n + 1), [])
  return { data, error, loading, reload }
}
