import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, loginUrl, unwrap, type SessionUser } from '../api/client'
import { Spinner } from '../components'

interface SessionState {
  /** undefined while loading, null when nobody is signed in. */
  user: SessionUser | null | undefined
  refresh: () => Promise<void>
}

const SessionContext = createContext<SessionState | null>(null)

export function SessionProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [user, setUser] = useState<SessionUser | null>()

  const refresh = useCallback(async () => {
    try {
      const body = unwrap(await api.GET('/api/v1/session'))
      setUser(body.user ?? null)
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo(() => ({ user, refresh }), [user, refresh])
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionState {
  const value = useContext(SessionContext)
  if (!value) throw new Error('useSession needs a SessionProvider')
  return value
}

/** Screens that need a Discord sign-in: send a signed-out visitor to Discord and back. */
export function RequireSignIn({ children }: Readonly<{ children: (user: SessionUser) => ReactNode }>) {
  const { user } = useSession()
  useEffect(() => {
    if (user === null) window.location.assign(loginUrl())
  }, [user])
  if (user === undefined) return <Spinner label="Loading" />
  if (user === null) return <Spinner label="Taking you to Discord to sign in" />
  return <>{children(user)}</>
}
