import { createContext, useContext } from 'react'
import type { ServerDetail } from '../api/client'

export interface ServerContextValue {
  /** GET /api/v1/servers/{guild_id}: the server's name, channels and roles. */
  server: ServerDetail
  /** Load the server again, after a change to its channels or roles. */
  reload: () => void
}

export const ServerContext = createContext<ServerContextValue | null>(null)

/** The server whose page a section is on. Only for components under ServerScreen. */
export function useServer(): ServerContextValue {
  const value = useContext(ServerContext)
  if (!value) throw new Error('useServer() is only for sections of a server page')
  return value
}
