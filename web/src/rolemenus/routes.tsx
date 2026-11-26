import { useParams } from 'react-router-dom'
import { RequireSignIn } from '../auth/SessionProvider'
import { PageHeader } from '../components'
import { RoleMenuEditor } from './RoleMenuFormScreen'
import { RoleMenusSection } from './RoleMenusScreen'

/**
 * /servers/:guildId/role-menus, /new and /:menuId. These become child routes of
 * the server page once it lands; until then each stands alone, so it checks
 * sign-in itself (the API checks the viewer administers the server).
 */
export function RoleMenusRoute() {
  const { guildId = '' } = useParams()
  return (
    <RequireSignIn>
      {() => (
        <>
          <PageHeader title="Role menus" />
          <RoleMenusSection guildId={guildId} />
        </>
      )}
    </RequireSignIn>
  )
}

export function RoleMenuEditorRoute() {
  const { guildId = '', menuId } = useParams()
  return <RequireSignIn>{() => <RoleMenuEditor guildId={guildId} menuId={menuId ? Number(menuId) : undefined} />}</RequireSignIn>
}
