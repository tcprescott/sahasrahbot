import { Navigate } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'

/** /presets/me: your own namespace, made the first time you come here. */
export function MyPresetsScreen() {
  return <RequireSignIn>{() => <Mine />}</RequireSignIn>
}

function Mine() {
  const query = useQuery('presets/mine', async () => unwrap(await api.GET('/api/v1/presets/mine')))
  return (
    <Loaded query={query} label="Finding your presets">
      {(mine) => <Navigate to={`/presets/manage/${encodeURIComponent(mine.namespace)}`} replace />}
    </Loaded>
  )
}
