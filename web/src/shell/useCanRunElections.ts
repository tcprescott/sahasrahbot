import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useSession } from '../auth/SessionProvider'

/**
 * Whether the signed-in person administers a server SahasrahBot is in, so the
 * Elections tab is theirs to see. The shell asks once and hands the answer to
 * both copies of the nav.
 */
export function useCanRunElections(): boolean {
  const { user } = useSession()
  const id = user?.id
  const [can, setCan] = useState(false)
  useEffect(() => {
    setCan(false)
    if (!id) return
    let live = true
    api
      .GET('/api/v1/elections/servers')
      .then(({ data }) => {
        if (live) setCan((data?.servers.length ?? 0) > 0)
      })
      .catch(() => {})
    return () => {
      live = false
    }
  }, [id])
  return can
}
