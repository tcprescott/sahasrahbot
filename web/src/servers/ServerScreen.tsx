import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Icon } from '../components'
import { initials } from './initials'
import { ServerContext } from './ServerContext'
import { SECTIONS, serverPath } from './sections'
import './servers.css'

/**
 * /servers/:guildId/:section — one server's page: its name, a switcher to your
 * other servers, the section tabs, and the section itself (a child route).
 */
export function ServerScreen() {
  return <RequireSignIn>{() => <Server />}</RequireSignIn>
}

function Server() {
  const { guildId = '' } = useParams()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const query = useQuery(`servers/${guildId}`, async () =>
    unwrap(await api.GET('/api/v1/servers/{guild_id}', { params: { path: { guild_id: guildId as unknown as number } } })),
  )
  const others = useQuery('servers', async () => unwrap(await api.GET('/api/v1/servers')).servers)
  const section = SECTIONS.find((s) => pathname.startsWith(serverPath(guildId, s.key)))

  return (
    <>
      <nav className="server-crumb" aria-label="Breadcrumb">
        <Link to="/servers">Servers</Link>
        <Icon name="chevron_right" size={16} />
      </nav>
      <Loaded query={query} label="Loading the server" notFound="SahasrahBot isn't in that server.">
        {(server) => (
          <ServerContext.Provider value={{ server, reload: query.reload }}>
            <header className="server-head">
              <span className="server-badge" aria-hidden="true">
                {initials(server.name)}
              </span>
              <h1>{server.name}</h1>
              {(others.data?.length ?? 0) > 1 && (
                <select
                  className="input server-head__switch"
                  aria-label="Switch server"
                  value={server.id}
                  onChange={(e) => navigate(serverPath(e.target.value, section?.key))}
                >
                  {others.data?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
            </header>
            <nav className="detail-tabs server-tabs" aria-label="Server sections">
              {SECTIONS.map((s) => (
                // NavLink marks the tab active on its section and anything under it.
                <NavLink key={s.key} to={serverPath(server.id, s.key)}>
                  {s.label}
                </NavLink>
              ))}
            </nav>
            <Outlet />
          </ServerContext.Provider>
        )}
      </Loaded>
    </>
  )
}
