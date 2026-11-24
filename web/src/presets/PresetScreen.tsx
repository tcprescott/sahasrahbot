import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { ActionsMenu, Banner, Button, ConfirmDialog, Icon, PageHeader, Panel } from '../components'
import { browser } from '../lib/browser'
import { fullDate } from '../lib/time'
import { downloadPath, namespacePath, presetParams } from './paths'
import { YamlField } from './YamlField'

/** /presets/manage/:namespace/:randomizer/:preset — read it, and edit it if it's yours (?edit=1). */
export function PresetScreen() {
  const { namespace = '', randomizer = '', preset = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const editing = params.get('edit') === '1'
  const navigate = useNavigate()
  const query = useQuery(`presets/${namespace}/${randomizer}/${preset}`, async () =>
    unwrap(
      await api.GET('/api/v1/presets/namespaces/{namespace}/{randomizer}/{preset}', presetParams(namespace, randomizer, preset)),
    ),
  )
  const [draft, setDraft] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const [deleting, setDeleting] = useState(false)

  const setEditing = (on: boolean) => {
    setDraft(null)
    setError(undefined)
    setParams(on ? { edit: '1' } : {}, { replace: true })
  }

  return (
    <Loaded query={query} label="Loading the preset">
      {(p) => {
        const text = draft ?? p.content
        return (
          <>
            <Link to={namespacePath(p.namespace)} className="back-link">
              <Icon name="chevron_left" size={20} />
              {p.namespace}'s presets
            </Link>
            <PageHeader
              title={`${p.namespace}/${p.name}`}
              lede={
                <>
                  {p.randomizer} · changed {fullDate(p.modified)} · rolled {p.generated_count}{' '}
                  {p.generated_count === 1 ? 'time' : 'times'}
                </>
              }
              actions={
                !editing && (
                  <>
                    {p.can_edit && (
                      <Button icon="edit" onClick={() => setEditing(true)}>
                        Edit
                      </Button>
                    )}
                    {p.can_edit ? (
                      <ActionsMenu
                        items={[
                          {
                            label: 'Download',
                            icon: 'download',
                            onSelect: () => browser.assign(downloadPath(p.namespace, p.randomizer, p.name)),
                          },
                          { label: 'Delete', icon: 'delete', destructive: true, onSelect: () => setDeleting(true) },
                        ]}
                      />
                    ) : (
                      <Button asChild variant="outline">
                        <a href={downloadPath(p.namespace, p.randomizer, p.name)}>
                          <Icon name="download" size={18} />
                          Download
                        </a>
                      </Button>
                    )}
                  </>
                )
              }
            />
            {error && <Banner tone="error">{error}</Banner>}
            {editing && p.can_edit ? (
              <Panel title="Edit">
                <div className="panel__pad stack">
                  <YamlField value={text} onChange={setDraft} />
                  <div className="t-actions t-actions--end">
                    <Button variant="ghost" onClick={() => setEditing(false)}>
                      Cancel
                    </Button>
                    <Button
                      busy={busy}
                      busyLabel="Saving"
                      disabled={draft === null || draft === p.content}
                      onClick={async () => {
                        setBusy(true)
                        try {
                          unwrap(
                            await api.PUT('/api/v1/presets/namespaces/{namespace}/{randomizer}/{preset}', {
                              ...presetParams(p.namespace, p.randomizer, p.name),
                              body: { content: text },
                            }),
                          )
                          query.reload()
                          setEditing(false)
                        } catch (e) {
                          setError((e as Error).message)
                        } finally {
                          setBusy(false)
                        }
                      }}
                    >
                      Save
                    </Button>
                  </div>
                </div>
              </Panel>
            ) : (
              <Panel title="YAML">
                <pre className="yaml">
                  <code>{p.content}</code>
                </pre>
              </Panel>
            )}
            <ConfirmDialog
              open={deleting}
              onOpenChange={setDeleting}
              title={`Delete ${p.name}?`}
              action="Delete preset"
              onConfirm={async () => {
                try {
                  unwrap(
                    await api.DELETE(
                      '/api/v1/presets/namespaces/{namespace}/{randomizer}/{preset}',
                      presetParams(p.namespace, p.randomizer, p.name),
                    ),
                  )
                  navigate(namespacePath(p.namespace), { replace: true })
                } catch (e) {
                  setError((e as Error).message)
                }
              }}
            >
              {p.namespace}/{p.name} stops working in Discord straight away. This can't be undone.
            </ConfirmDialog>
          </>
        )
      }}
    </Loaded>
  )
}
