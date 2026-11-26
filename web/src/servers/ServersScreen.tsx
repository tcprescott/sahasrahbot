import { Link } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { EmptyState, Icon, PageHeader, Panel } from '../components'
import { serverPath } from './sections'
import { initials } from './initials'
import './servers.css'

/** /servers — the Discord servers you administer that SahasrahBot is in. */
export function ServersScreen() {
  return <RequireSignIn>{() => <Servers />}</RequireSignIn>
}

function Servers() {
  const query = useQuery('servers', async () => unwrap(await api.GET('/api/v1/servers')).servers)
  return (
    <>
      <PageHeader
        title="Servers"
        lede="The Discord servers you administer that SahasrahBot is in. Pick one to change how the bot behaves there."
      />
      <Loaded query={query} label="Loading your servers">
        {(servers) =>
          servers.length === 0 ? (
            <EmptyState icon="forum" title="No servers to manage">
              You aren't an Administrator of any server SahasrahBot is in.
            </EmptyState>
          ) : (
            <ul className="server-cards">
              {servers.map((s) => (
                <li key={s.id}>
                  <Panel>
                    <Link to={serverPath(s.id)} className="server-card">
                      <span className="server-badge" aria-hidden="true">
                        {initials(s.name)}
                      </span>
                      <span className="server-card__name">{s.name}</span>
                      <Icon name="chevron_right" />
                    </Link>
                  </Panel>
                </li>
              ))}
            </ul>
          )
        }
      </Loaded>
    </>
  )
}
