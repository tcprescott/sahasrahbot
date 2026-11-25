import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, EmptyState, Icon, PageHeader, Panel } from '../components'
import { namespacePath, presetParams, presetPath } from './paths'
import { YamlField } from './YamlField'

const NAME = /^\w{1,50}$/

export function NewPresetScreen() {
  return <RequireSignIn>{() => <NewPreset />}</RequireSignIn>
}

function NewPreset() {
  const { namespace = '' } = useParams()
  const navigate = useNavigate()
  const query = useQuery(`presets/new/${namespace}`, async () => {
    const [ns, randomizers] = await Promise.all([
      api.GET('/api/v1/presets/namespaces/{namespace}', { params: { path: { namespace } } }).then(unwrap),
      api.GET('/api/v1/presets/randomizers').then(unwrap),
    ])
    return { ns, randomizers: randomizers.randomizers }
  })
  const [name, setName] = useState('')
  const [randomizer, setRandomizer] = useState('alttpr')
  const [content, setContent] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const nameOk = NAME.test(name)

  return (
    <Loaded query={query} label="Loading">
      {({ ns, randomizers }) =>
        !ns.can_edit ? (
          <EmptyState icon="folder" title="This isn't your namespace">
            Only {ns.name} and their collaborators can add presets here. <Link to="/presets/me">Go to your presets</Link>.
          </EmptyState>
        ) : (
          <>
            <Link to={namespacePath(ns.name)} className="back-link">
              <Icon name="chevron_left" size={20} />
              {ns.name}'s presets
            </Link>
            <PageHeader title="New preset" lede="Saving a name that already exists for that randomizer replaces it." />
            {error && <Banner tone="error">{error}</Banner>}
            <Panel>
              <form
                className="panel__pad stack"
                onSubmit={async (e) => {
                  e.preventDefault()
                  setBusy(true)
                  try {
                    const saved = unwrap(
                      await api.PUT('/api/v1/presets/namespaces/{namespace}/{randomizer}/{preset}', {
                        ...presetParams(ns.name, randomizer, name),
                        body: { content },
                      }),
                    )
                    navigate(presetPath(saved.namespace, saved.randomizer, saved.name))
                  } catch (err) {
                    setError((err as Error).message)
                    setBusy(false)
                  }
                }}
              >
                <div className="field-grid">
                  <div className="field">
                    <label className="field__label" htmlFor="preset-name">
                      Name
                    </label>
                    <input
                      id="preset-name"
                      className="input"
                      value={name}
                      maxLength={50}
                      autoComplete="off"
                      aria-describedby="preset-name-hint"
                      aria-invalid={name !== '' && !nameOk}
                      onChange={(e) => setName(e.target.value)}
                    />
                    <span id="preset-name-hint" className="field__hint">
                      Letters, numbers and underscores. Rolled as{' '}
                      <span className="code">
                        {ns.name}/{name || 'name'}
                      </span>
                      .
                    </span>
                  </div>
                  <div className="field">
                    <label className="field__label" htmlFor="preset-randomizer">
                      Randomizer
                    </label>
                    <select
                      id="preset-randomizer"
                      className="input"
                      value={randomizer}
                      onChange={(e) => setRandomizer(e.target.value)}
                    >
                      {randomizers.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <YamlField value={content} onChange={setContent} onProblem={setProblem} randomizer={randomizer} />
                <div className="t-actions t-actions--end">
                  <Button variant="ghost" onClick={() => navigate(namespacePath(ns.name))}>
                    Cancel
                  </Button>
                  <Button type="submit" busy={busy} busyLabel="Saving" disabled={!nameOk || !content.trim() || problem !== null}>
                    Save preset
                  </Button>
                </div>
              </form>
            </Panel>
          </>
        )
      }
    </Loaded>
  )
}
