import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Icon } from '../components'
import { browser } from '../lib/browser'
import './apiaccess.css'

const READS = [
  'Your profile and linked racetime.gg account',
  'Presets, and rolling seeds from them',
  'Seeds by hash',
  'Elections, ballots and results',
  'Triforce texts',
  'Tournament settings forms',
]
const CHANGES = 'Save and delete your presets, vote in elections, create and run elections in servers you administer, submit and moderate triforce texts, and submit tournament settings.'

/**
 * /oauth/consent?txn=… — where an AI client (Claude, say) sends you to approve it.
 * Outside the app shell: it's a stop on the way back to the client, not a page of the app.
 */
export function ConsentScreen() {
  return (
    <div className="consent-page">
      <div className="consent-brand">
        <img className="brand__mark" src="/sahasrahbot.png" alt="" />
        <span>SahasrahBot</span>
      </div>
      <RequireSignIn>{(user) => <Consent userName={user.name} />}</RequireSignIn>
    </div>
  )
}

function Consent({ userName }: Readonly<{ userName: string }>) {
  const txn = useSearchParams()[0].get('txn') ?? ''
  const query = useQuery(`oauth-${txn}`, async () =>
    unwrap(await api.GET('/api/v1/oauth/requests/{txn}', { params: { path: { txn } } })),
  )
  const [allowChanges, setAllowChanges] = useState(false)
  const [busy, setBusy] = useState<'approve' | 'deny'>()
  const [error, setError] = useState<string>()

  const answer = async (approve: boolean) => {
    setBusy(approve ? 'approve' : 'deny')
    try {
      const path = { params: { path: { txn } } }
      const done = approve
        ? unwrap(await api.POST('/api/v1/oauth/requests/{txn}/approve', { ...path, body: { allow_changes: allowChanges } }))
        : unwrap(await api.POST('/api/v1/oauth/requests/{txn}/deny', path))
      browser.assign(done.redirect_url)
    } catch (e) {
      setError((e as Error).message)
      setBusy(undefined)
    }
  }

  return (
    <section className="panel consent">
      <Loaded query={query} label="Loading the request">
        {(request) => (
          <>
            <div className="panel__pad stack">
              <h1 className="consent__title">{request.client_name} wants to use your SahasrahBot account</h1>
              <p className="muted consent__lede">
                Signed in as <b>{userName}</b>. Approving sends you back to <span className="code">{request.redirect_target}</span>.
              </p>
              {error && <Banner tone="error">{error}</Banner>}
              <div>
                <h2 className="consent__heading">It will be able to see</h2>
                <ul className="consent__list">
                  {READS.map((r) => (
                    <li key={r}>
                      <Icon name="visibility" size={18} /> {r}
                    </li>
                  ))}
                </ul>
              </div>
              <label className="choice-tile">
                <input type="checkbox" checked={allowChanges} onChange={(e) => setAllowChanges(e.target.checked)} />
                <div>
                  <b>Also let it make changes as you</b>
                  <span className="choice-tile__desc">{CHANGES}</span>
                </div>
              </label>
              <span className="muted">You can disconnect it at any time on the API access page.</span>
            </div>
            <footer className="dialog__foot">
              <Button variant="outline" onClick={() => void answer(false)} busy={busy === 'deny'} busyLabel="Denying" disabled={busy !== undefined}>
                Deny
              </Button>
              <Button onClick={() => void answer(true)} busy={busy === 'approve'} busyLabel="Approving" disabled={busy !== undefined}>
                Approve
              </Button>
            </footer>
          </>
        )}
      </Loaded>
    </section>
  )
}
