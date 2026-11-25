import { Link, useSearchParams } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Chip, PageHeader, Panel, PanelRow } from '../components'

export function MeScreen() {
  return <RequireSignIn>{() => <Me />}</RequireSignIn>
}

function Me() {
  const [params] = useSearchParams()
  const linked = params.get('racetime')
  const query = useQuery('me', async () => unwrap(await api.GET('/api/v1/me')))
  return (
    <Loaded query={query} label="Loading your profile">
      {(me) => (
        <>
          <PageHeader title={me.user.name} lede="What SahasrahBot knows about your Discord account." />
          {linked && (
            <Banner tone="accent">
              Linked racetime.gg account <strong>{linked}</strong>. Tournament races can now invite you.
            </Banner>
          )}
          <Panel title="racetime.gg">
            <PanelRow>
              <div className="grow">
                {me.racetime_linked ? (
                  <>
                    <Chip tone="ok">Linked</Chip> <span className="muted mono">{me.racetime_id}</span>
                  </>
                ) : (
                  <>
                    <Chip tone="pending">Not linked</Chip>{' '}
                    <span className="muted">Link it so tournament races can invite you.</span>
                  </>
                )}
              </div>
              <Button asChild variant={me.racetime_linked ? 'outline' : 'primary'}>
                <a href="/racetime/verification/initiate">{me.racetime_linked ? 'Link again' : 'Link racetime.gg'}</a>
              </Button>
            </PanelRow>
          </Panel>
          <Panel title="Presets">
            <PanelRow>
              <div className="grow">
                {me.preset_namespace ? (
                  <>
                    Your namespace is <span className="code">{me.preset_namespace}</span>
                  </>
                ) : (
                  <span className="muted">You haven't made any presets yet.</span>
                )}
              </div>
              <Button asChild variant="outline">
                <Link to="/presets/me">My presets</Link>
              </Button>
            </PanelRow>
          </Panel>
          {me.moderated_triforce_pools.length > 0 && (
            <Panel title="Triforce texts you moderate">
              {me.moderated_triforce_pools.map((pool) => (
                <PanelRow key={pool}>
                  <span className="grow mono">
                    {pool}
                  </span>
                  <Button asChild variant="outline" size="sm">
                    <Link to={`/triforcetexts/${encodeURIComponent(pool)}/moderation`}>Review</Link>
                  </Button>
                </PanelRow>
              ))}
            </Panel>
          )}
          <Panel title="API access">
            <PanelRow>
              <span className="grow muted">Tokens for your own scripts, and AI clients like Claude connected to your account.</span>
              <Button asChild variant="outline">
                <Link to="/me/api">API access</Link>
              </Button>
            </PanelRow>
          </Panel>
          <Panel title="Audit log">
            <PanelRow>
              <span className="grow muted">
                Every change made through SahasrahBot: yours, and everyone's in the servers you run.
              </span>
              <Button asChild variant="outline">
                <Link to="/audit">Audit log</Link>
              </Button>
            </PanelRow>
          </Panel>
          <Panel title="Your data">
            <PanelRow>
              <span className="grow muted">
                Delete your presets, nickname verifications and API tokens, and sign out.
              </span>
              <Button asChild variant="outline">
                <Link to="/purgeme">Delete my data</Link>
              </Button>
            </PanelRow>
          </Panel>
        </>
      )}
    </Loaded>
  )
}
