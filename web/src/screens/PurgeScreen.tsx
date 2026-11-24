import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { RequireSignIn, useSession } from '../auth/SessionProvider'
import { Banner, Button, ConfirmDialog, PageHeader, Panel } from '../components'

export function PurgeScreen() {
  return <RequireSignIn>{() => <Purge />}</RequireSignIn>
}

function Purge() {
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string>()
  const { refresh } = useSession()
  const navigate = useNavigate()
  return (
    <>
      <PageHeader title="Delete my data" lede="Remove what SahasrahBot keeps about your Discord account." />
      {error && <Banner tone="error">{error}</Banner>}
      <Panel title="What gets deleted">
        <div className="prose panel__pad">
          <ul>
            <li>Your preset namespace and every preset in it.</li>
            <li>Your nickname verifications.</li>
            <li>Your API tokens, and the AI clients you connected.</li>
          </ul>
          <p className="muted">
            Everything else, like race results and your racetime.gg link, stays. This can't be
            undone.
          </p>
        </div>
      </Panel>
      <div className="t-actions">
        <Button variant="outline" onClick={() => navigate('/me')}>
          Keep my data
        </Button>
        <Button variant="danger" icon="delete" onClick={() => setOpen(true)}>
          Delete my data
        </Button>
      </div>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Delete your data?"
        action="Delete and sign out"
        onConfirm={async () => {
          try {
            unwrap(await api.POST('/api/v1/me/purge'))
          } catch (e) {
            setError((e as Error).message)
            return
          }
          await refresh()
          navigate('/', { replace: true })
        }}
      >
        Your presets, nickname verifications and API tokens are deleted for good, and you're signed out.
      </ConfirmDialog>
    </>
  )
}
