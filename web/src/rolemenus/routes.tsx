import { useParams } from 'react-router-dom'
import { useServer } from '../servers/ServerContext'
import { RoleMenuEditor } from './RoleMenuFormScreen'
import { RoleMenusSection } from './RoleMenusScreen'

/**
 * The Role menus section of a server's page: child routes of servers/:guildId
 * (`role-menus`, `role-menus/new`, `role-menus/:menuId`). ServerScreen checks
 * sign-in and draws the server's header and tabs.
 */
export function RoleMenusRoute() {
  const { server } = useServer()
  return <RoleMenusSection guildId={server.id} />
}

export function RoleMenuEditorRoute() {
  const { server } = useServer()
  const { menuId } = useParams()
  return <RoleMenuEditor guildId={server.id} menuId={menuId ? Number(menuId) : undefined} />
}
