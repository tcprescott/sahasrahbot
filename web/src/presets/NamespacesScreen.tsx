import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { Button, Icon, PageHeader } from '../components'
import { DataTable } from '../kit/DataTable'

export function NamespacesScreen() {
  const query = useQuery('presets/namespaces', async () => unwrap(await api.GET('/api/v1/presets/namespaces')))
  const [filter, setFilter] = useState('')
  const needle = filter.trim().toLowerCase()
  const rows = useMemo(
    () => (query.data?.namespaces ?? []).filter((ns) => ns.name.toLowerCase().includes(needle)),
    [query.data, needle],
  )
  return (
    <>
      <PageHeader
        title="Presets"
        lede={
          <>
            Everyone's uploaded presets. Roll one in Discord by giving <span className="code">namespace/preset</span> as
            the preset.
          </>
        }
        actions={
          <Button asChild>
            <Link to="/presets/me">My presets</Link>
          </Button>
        }
      />
      <Loaded query={query} label="Loading presets">
        {() => (
          <div className="stack">
            <label className="search-box">
              <Icon name="search" size={20} />
              <span className="visually-hidden">Find a namespace</span>
              <input
                className="search-box__input"
                type="search"
                placeholder="Find a namespace"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            </label>
            <DataTable
              label="Preset namespaces"
              rowKey={(ns) => ns.name}
              rows={rows}
              empty={{ icon: 'folder', title: needle ? `No namespace matches "${filter.trim()}"` : 'No presets yet' }}
              columns={[
                {
                  key: 'name',
                  header: 'Namespace',
                  primary: true,
                  render: (ns) => <Link to={`/presets/manage/${encodeURIComponent(ns.name)}`}>{ns.name}</Link>,
                },
                {
                  key: 'count',
                  header: 'Presets',
                  align: 'end',
                  render: (ns) => ns.preset_count,
                },
              ]}
            />
          </div>
        )}
      </Loaded>
    </>
  )
}
