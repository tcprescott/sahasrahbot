import { useState } from 'react'
import { api, unwrap, type ApiTokenRow } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Chip, ConfirmDialog, FormDialog, PageHeader, Panel } from '../components'
import { DataTable } from '../kit/DataTable'
import { ago, fullDate } from '../lib/time'
import { CopyField } from './CopyField'
import './apiaccess.css'

/** /me/api — personal access tokens for the REST API, and connected AI clients (MCP). */
export function ApiAccessScreen() {
  return <RequireSignIn>{() => <ApiAccess />}</RequireSignIn>
}

type Expiry = '30' | '90' | '365' | 'never'

function AccessChip({ readOnly }: Readonly<{ readOnly: boolean }>) {
  return readOnly ? <Chip tone="neutral">Read only</Chip> : <Chip tone="pending">Can make changes</Chip>
}

function ApiAccess() {
  const query = useQuery('tokens', async () => unwrap(await api.GET('/api/v1/tokens')))
  const [making, setMaking] = useState(false)
  const [revoking, setRevoking] = useState<ApiTokenRow>()
  const [error, setError] = useState<string>()

  const revoke = async (row: ApiTokenRow) => {
    try {
      unwrap(await api.DELETE('/api/v1/tokens/{token_id}', { params: { path: { token_id: row.id } } }))
      setError(undefined)
      query.reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Loaded query={query} label="Loading your tokens">
      {({ tokens, mcp_url }) => (
        <>
          <PageHeader
            title="API access"
            lede="Tokens for your own scripts, and the AI clients you've connected. Each one acts as you."
            actions={
              <Button icon="add" onClick={() => setMaking(true)}>
                New token
              </Button>
            }
          />
          {error && <Banner tone="error">{error}</Banner>}
          <Panel title="Connect an AI client">
            <div className="panel__pad stack">
              <CopyField value={mcp_url} label="Copy the MCP address" />
              <div className="api-setup">
                <div>
                  <b>Claude (web or desktop)</b>
                  <span className="muted">
                    Settings, then Connectors, then Add custom connector. Paste the address above, then sign in with Discord.
                  </span>
                </div>
                <div>
                  <b>Claude Code</b>
                  <span className="code api-setup__cmd">claude mcp add --transport http sahasrahbot {mcp_url}</span>
                </div>
              </div>
            </div>
          </Panel>
          <Panel title="Your tokens and clients">
            <DataTable
              label="Tokens and clients"
              rows={tokens}
              rowKey={(t) => t.id}
              empty={{ icon: 'key', title: 'No tokens or clients yet', body: 'Press New token to make one, or connect an AI client.' }}
              columns={[
                {
                  key: 'name',
                  header: 'Name',
                  primary: true,
                  render: (t) => (
                    <span className="api-name">
                      <b>{t.name}</b>
                      {t.prefix && <span className="muted mono">{t.prefix}…</span>}
                    </span>
                  ),
                },
                { key: 'kind', header: 'Kind', render: (t) => (t.kind === 'client' ? 'AI client' : 'Token') },
                { key: 'access', header: 'Access', render: (t) => <AccessChip readOnly={t.read_only} /> },
                {
                  key: 'used',
                  header: 'Last used',
                  render: (t) => (t.last_used_at ? <span title={fullDate(t.last_used_at)}>{ago(t.last_used_at)}</span> : 'Never'),
                },
                {
                  key: 'expires',
                  header: 'Expires',
                  desktopOnly: true,
                  render: (t) => {
                    if (t.kind === 'client') return 'Until you disconnect'
                    return t.expires_at ? fullDate(t.expires_at) : 'Never'
                  },
                },
              ]}
              rowMenu={(t) => [
                { label: t.kind === 'client' ? 'Disconnect' : 'Revoke', icon: 'delete', destructive: true, onSelect: () => setRevoking(t) },
              ]}
              rowMenuLabel={(t) => `More for ${t.name}`}
            />
          </Panel>
          <p className="muted api-footnote">
            Scripts send a token as <span className="code">Authorization: Bearer sb_pat_…</span>. Every endpoint is in the{' '}
            <a href="/api/v1/docs">API docs</a>.
          </p>
          <NewTokenDialog
            open={making}
            onClose={() => {
              setMaking(false)
              query.reload()
            }}
          />
          <ConfirmDialog
            open={revoking !== undefined}
            onOpenChange={(open) => !open && setRevoking(undefined)}
            title={revoking?.kind === 'client' ? 'Disconnect this AI client?' : 'Revoke this token?'}
            action={revoking?.kind === 'client' ? 'Disconnect' : 'Revoke'}
            onConfirm={async () => revoking && revoke(revoking)}
          >
            {revoking?.kind === 'client'
              ? `“${revoking?.name}” stops working straight away. You can connect it again later.`
              : `Anything using “${revoking?.name}” stops working straight away. This can't be undone.`}
          </ConfirmDialog>
        </>
      )}
    </Loaded>
  )
}

function NewTokenDialog({ open, onClose }: Readonly<{ open: boolean; onClose: () => void }>) {
  const [name, setName] = useState('')
  const [readOnly, setReadOnly] = useState(true)
  const [expiry, setExpiry] = useState<Expiry>('90')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const [made, setMade] = useState<{ token: string; row: ApiTokenRow }>()

  const close = () => {
    setName('')
    setReadOnly(true)
    setExpiry('90')
    setError(undefined)
    setMade(undefined)
    onClose()
  }

  const make = async () => {
    setBusy(true)
    try {
      const body = {
        name,
        read_only: readOnly,
        expires_in_days: expiry === 'never' ? null : (Number(expiry) as 30 | 90 | 365),
      }
      setMade(unwrap(await api.POST('/api/v1/tokens', { body })))
      setError(undefined)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (made) {
    const { row } = made
    return (
      <FormDialog open={open} onOpenChange={(o) => !o && close()} title="Copy your token now" size="sm" primaryLabel="Done" onPrimary={close} cancelLabel="Close">
        <div className="stack">
          <Banner tone="warning">This is the only time you'll see it. If you lose it, revoke it and make another.</Banner>
          <CopyField value={made.token} label="Copy the token" />
          <span className="muted">
            {row.name} · {row.read_only ? 'read only' : 'can make changes'} · {row.expires_at ? `expires ${fullDate(row.expires_at)}` : 'never expires'}
          </span>
        </div>
      </FormDialog>
    )
  }

  return (
    <FormDialog
      open={open}
      onOpenChange={(o) => !o && close()}
      title="New token"
      size="sm"
      primaryLabel="Make token"
      onPrimary={() => void make()}
      busy={busy}
      busyLabel="Making the token"
    >
      <div className="stack">
        {error && <Banner tone="error">{error}</Banner>}
        <div className="field">
          <label className="field__label" htmlFor="token-name">
            Name
          </label>
          <input id="token-name" className="input" value={name} maxLength={100} onChange={(e) => setName(e.target.value)} />
          <span className="field__hint">So you can tell your tokens apart.</span>
        </div>
        <fieldset className="field api-fieldset">
          <legend className="field__label">Access</legend>
          <label className="choice-tile">
            <input type="radio" name="access" checked={readOnly} onChange={() => setReadOnly(true)} />
            <div>
              <b>Read only</b>
              <span className="choice-tile__desc">See presets, seeds, elections and texts, and roll seeds.</span>
            </div>
          </label>
          <label className="choice-tile">
            <input type="radio" name="access" checked={!readOnly} onChange={() => setReadOnly(false)} />
            <div>
              <b>Read and make changes</b>
              <span className="choice-tile__desc">Also save presets, vote, submit texts and run your elections.</span>
            </div>
          </label>
        </fieldset>
        <div className="field">
          <label className="field__label" htmlFor="token-expiry">
            Expires
          </label>
          <select id="token-expiry" className="input" value={expiry} onChange={(e) => setExpiry(e.target.value as Expiry)}>
            <option value="30">In 30 days</option>
            <option value="90">In 90 days</option>
            <option value="365">In a year</option>
            <option value="never">Never</option>
          </select>
        </div>
      </div>
    </FormDialog>
  )
}
