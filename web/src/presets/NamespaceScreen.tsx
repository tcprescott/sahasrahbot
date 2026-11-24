import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, unwrap, type PresetSummary } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { Banner, Button, ConfirmDialog, PageHeader } from '../components'
import { DataTable } from '../kit/DataTable'
import { ago, fullDate } from '../lib/time'
import { downloadPath, namespacePath, presetParams, presetPath } from './paths'

/** One namespace's presets: /presets/manage/:namespace, filtered by /:randomizer. */
export function NamespaceScreen() {
  const { namespace = '', randomizer } = useParams()
  const navigate = useNavigate()
  const query = useQuery(`presets/ns/${namespace}`, async () =>
    unwrap(await api.GET('/api/v1/presets/namespaces/{namespace}', { params: { path: { namespace } } })),
  )
  const [deleting, setDeleting] = useState<PresetSummary | null>(null)
  const [error, setError] = useState<string>()

  return (
    <Loaded query={query} label="Loading presets" notFound={`There's no namespace called ${namespace}.`}>
      {(ns) => {
        const counts = new Map<string, number>()
        for (const p of ns.presets) counts.set(p.randomizer, (counts.get(p.randomizer) ?? 0) + 1)
        const rows = randomizer ? ns.presets.filter((p) => p.randomizer === randomizer) : ns.presets
        return (
          <>
            <PageHeader
              title={`${ns.name}'s presets`}
              lede={
                <>
                  Roll one in Discord by giving <span className="code">{ns.name}/&lt;preset&gt;</span> as the preset.
                </>
              }
              actions={
                ns.can_edit && (
                  <Button asChild>
                    <Link to={`/presets/${encodeURIComponent(ns.name)}/create`}>New preset</Link>
                  </Button>
                )
              }
            />
            {error && <Banner tone="error">{error}</Banner>}
            <div className="stack">
              {counts.size > 1 && (
                <div className="filter-chips" role="group" aria-label="Randomizer">
                  <button
                    type="button"
                    className="filter-chip"
                    aria-pressed={!randomizer}
                    onClick={() => navigate(namespacePath(ns.name))}
                  >
                    All <span className="filter-chips__n">{ns.presets.length}</span>
                  </button>
                  {[...counts].map(([r, n]) => (
                    <button
                      key={r}
                      type="button"
                      className="filter-chip"
                      aria-pressed={randomizer === r}
                      onClick={() => navigate(namespacePath(ns.name, r))}
                    >
                      {r} <span className="filter-chips__n">{n}</span>
                    </button>
                  ))}
                </div>
              )}
              <DataTable
                label={`${ns.name}'s presets`}
                rows={rows}
                rowKey={(p) => `${p.randomizer}/${p.name}`}
                empty={{
                  icon: 'folder',
                  title: ns.can_edit ? "You haven't made any presets yet" : 'No presets here yet',
                  body: ns.can_edit ? 'Use New preset to upload a YAML file or paste one in.' : undefined,
                }}
                columns={[
                  {
                    key: 'name',
                    header: 'Name',
                    primary: true,
                    cell: (p) => <Link to={presetPath(ns.name, p.randomizer, p.name)}>{p.name}</Link>,
                  },
                  { key: 'randomizer', header: 'Randomizer', cell: (p) => p.randomizer },
                  {
                    key: 'modified',
                    header: 'Changed',
                    cell: (p) => (
                      <span className="muted" title={fullDate(p.modified)}>
                        {ago(p.modified)}
                      </span>
                    ),
                  },
                  { key: 'rolled', header: 'Rolled', align: 'end', cell: (p) => p.generated_count },
                ]}
                rowAction={(p) => (
                  <Button asChild variant="outline" size="sm">
                    <a href={downloadPath(ns.name, p.randomizer, p.name)} aria-label={`Download ${p.name}`}>
                      Download
                    </a>
                  </Button>
                )}
                rowMenuLabel={(p) => `More for ${p.name}`}
                rowMenu={(p) =>
                  ns.can_edit
                    ? [
                        {
                          label: 'Edit',
                          icon: 'edit',
                          onSelect: () => navigate(`${presetPath(ns.name, p.randomizer, p.name)}?edit=1`),
                        },
                        { label: 'Delete', icon: 'delete', destructive: true, onSelect: () => setDeleting(p) },
                      ]
                    : []
                }
              />
            </div>
            <ConfirmDialog
              open={deleting !== null}
              onOpenChange={(open) => !open && setDeleting(null)}
              title={`Delete ${deleting?.name ?? ''}?`}
              action="Delete preset"
              onConfirm={async () => {
                if (!deleting) return true
                try {
                  unwrap(
                    await api.DELETE(
                      '/api/v1/presets/namespaces/{namespace}/{randomizer}/{preset}',
                      presetParams(ns.name, deleting.randomizer, deleting.name),
                    ),
                  )
                  setError(undefined)
                  query.reload()
                } catch (e) {
                  setError((e as Error).message)
                }
                return true
              }}
            >
              {ns.name}/{deleting?.name} ({deleting?.randomizer}) stops working in Discord straight away. This can't be
              undone.
            </ConfirmDialog>
          </>
        )
      }}
    </Loaded>
  )
}
