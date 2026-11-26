import { useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, unwrap, type RacerVerification } from '../../api/client'
import { Banner, Button, Panel } from '../../components'
import { useServer } from '../ServerContext'

type Body = {
  role_id: string
  channel_id: string
  racetime_categories: string[]
  use_alttpr_ladder: boolean
  minimum_races: number
  time_period_days: number
  reverify_period_days: number | null
  revoke_ineligible: boolean
  audit_channel_id: string | null
}

interface Draft {
  roleId: string
  channelId: string
  categories: string[]
  ladder: boolean
  /** Number inputs are text while someone retypes them. */
  minimum: string
  period: string
  recheck: string
  revoke: boolean
  auditChannelId: string
}

function draftOf(v: RacerVerification | undefined): Draft {
  return {
    roleId: v?.role_id ?? '',
    channelId: v?.channel_id ?? '',
    categories: v?.racetime_categories ?? ['alttpr'],
    ladder: v?.use_alttpr_ladder ?? false,
    minimum: String(v?.minimum_races ?? 1),
    period: String(v?.time_period_days ?? 365),
    recheck: v?.reverify_period_days ? String(v.reverify_period_days) : '',
    revoke: v?.revoke_ineligible ?? false,
    auditChannelId: v?.audit_channel_id ?? '',
  }
}

/** The whole number typed, or undefined when it isn't one. */
function wholeNumber(text: string): number | undefined {
  return /^\d+$/.test(text.trim()) ? Number(text.trim()) : undefined
}

export function check(draft: Draft): string | undefined {
  if (!draft.roleId) return 'Pick the role to give.'
  if (!draft.channelId) return 'Pick the channel for the Verify button.'
  if (draft.categories.length === 0 && !draft.ladder) return 'Pick at least one racetime.gg category, or count ALTTPR Ladder races.'
  const minimum = wholeNumber(draft.minimum)
  if (minimum === undefined || minimum < 1) return 'Races needed must be 1 or more.'
  const period = wholeNumber(draft.period)
  if (period === undefined || period < 1) return 'The counting period must be 1 day or more.'
  if (draft.recheck.trim() && (wholeNumber(draft.recheck) ?? 0) < 1) return 'Recheck every must be 1 day or more, or empty.'
  return undefined
}

function bodyOf(draft: Draft): Body {
  const recheck = draft.recheck.trim() ? Number(draft.recheck) : null
  return {
    role_id: draft.roleId,
    channel_id: draft.channelId,
    racetime_categories: draft.categories,
    use_alttpr_ladder: draft.ladder,
    minimum_races: Number(draft.minimum),
    time_period_days: Number(draft.period),
    reverify_period_days: recheck,
    revoke_ineligible: recheck !== null && draft.revoke,
    audit_channel_id: draft.auditChannelId || null,
  }
}

function Field({ id, label, hint, children }: Readonly<{ id: string; label: string; hint?: ReactNode; children: ReactNode }>) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && (
        <span className="field__hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
    </div>
  )
}

/** Settings for a new or existing verification. Saving posts or updates the Discord message. */
export function VerificationForm({
  verification,
  categories,
  takenRoleIds,
  onSaved,
}: Readonly<{
  verification?: RacerVerification
  categories: string[]
  takenRoleIds: string[]
  onSaved: (saved: RacerVerification) => void
}>) {
  const { server } = useServer()
  const [draft, setDraft] = useState<Draft>(() => draftOf(verification))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const errorRef = useRef<HTMLDivElement>(null)
  const set = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }))

  // Categories saved before that the form doesn't list stay pickable.
  const offered = [...categories, ...draft.categories.filter((c) => !categories.includes(c))]
  const roles = server.roles.filter((r) => r.assignable !== false && !takenRoleIds.includes(r.id))
  const toggle = (slug: string) =>
    set({ categories: draft.categories.includes(slug) ? draft.categories.filter((c) => c !== slug) : [...draft.categories, slug] })

  const fail = (message: string) => {
    setError(message)
    requestAnimationFrame(() => errorRef.current?.scrollIntoView?.({ block: 'center' }))
  }

  const save = async () => {
    const problem = check(draft)
    if (problem) return fail(problem)
    setBusy(true)
    try {
      const body = bodyOf(draft)
      const saved = verification
        ? unwrap(await api.PUT('/api/v1/racer-verifications/{verification_id}', { params: { path: { verification_id: verification.id } }, body }))
        : unwrap(
            await api.POST('/api/v1/servers/{guild_id}/racer-verifications', {
              params: { path: { guild_id: server.id as unknown as number } },
              body,
            }),
          )
      setError(undefined)
      onSaved(saved)
    } catch (e) {
      fail((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const rechecks = draft.recheck.trim() !== ''
  return (
    <div className="stack">
      {error && (
        <div ref={errorRef}>
          <Banner tone="error">{error}</Banner>
        </div>
      )}
      <Panel title="Who qualifies">
        <div className="panel__pad stack">
          <div className="field-grid">
            <Field id="rv-role" label="Role to give" hint="SahasrahBot's own role must be above it.">
              <select id="rv-role" className="input" value={draft.roleId} onChange={(e) => set({ roleId: e.target.value })}>
                <option value="">Pick a role</option>
                {verification && !roles.some((r) => r.id === draft.roleId) && draft.roleId && (
                  <option value={draft.roleId}>{verification.role_name ? `@${verification.role_name}` : '@deleted role'}</option>
                )}
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    @{r.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field id="rv-channel" label="Post the Verify button in" hint={verification ? 'Changing it posts a new message there.' : undefined}>
              <select id="rv-channel" className="input" value={draft.channelId} onChange={(e) => set({ channelId: e.target.value })}>
                <option value="">Pick a channel</option>
                {server.text_channels.map((c) => (
                  <option key={c.id} value={c.id}>
                    #{c.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="field-grid">
            <Field id="rv-minimum" label="Races needed">
              <input id="rv-minimum" className="input" inputMode="numeric" value={draft.minimum} onChange={(e) => set({ minimum: e.target.value })} />
            </Field>
            <Field id="rv-period" label="Counted over the last" hint="days">
              <input id="rv-period" className="input" inputMode="numeric" value={draft.period} onChange={(e) => set({ period: e.target.value })} />
            </Field>
          </div>
          <fieldset className="field choice-fieldset">
            <legend className="field__label">Races that count</legend>
            <div className="filter-chips">
              {offered.map((slug) => (
                <button key={slug} type="button" className="filter-chip" aria-pressed={draft.categories.includes(slug)} onClick={() => toggle(slug)}>
                  {slug}
                </button>
              ))}
            </div>
            <span className="field__hint">Finished racetime.gg races in these categories.</span>
          </fieldset>
          <label className="t-check">
            <input type="checkbox" checked={draft.ladder} onChange={(e) => set({ ladder: e.target.checked })} /> Also count ALTTPR Ladder
            races
          </label>
        </div>
      </Panel>
      <Panel title="Keeping it current">
        <div className="panel__pad stack">
          <div className="field-grid">
            <Field id="rv-recheck" label="Recheck every" hint="days. Leave empty to never recheck.">
              <input id="rv-recheck" className="input" inputMode="numeric" value={draft.recheck} onChange={(e) => set({ recheck: e.target.value })} />
            </Field>
            <Field id="rv-audit" label="Report changes in">
              <select id="rv-audit" className="input" value={draft.auditChannelId} onChange={(e) => set({ auditChannelId: e.target.value })}>
                <option value="">Don't report</option>
                {server.text_channels.map((c) => (
                  <option key={c.id} value={c.id}>
                    #{c.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <label className="t-check">
            <input type="checkbox" checked={rechecks && draft.revoke} disabled={!rechecks} onChange={(e) => set({ revoke: e.target.checked })} />{' '}
            Take the role away from people who no longer qualify
          </label>
          <span className="field__hint">
            Only people who verified with the button are rechecked. Anyone given the role by hand is left alone. People who left the server
            are dropped from the list.
          </span>
        </div>
      </Panel>
      <div className="t-actions t-actions--end">
        {!verification && (
          <Button variant="ghost" asChild>
            <Link to={`/servers/${server.id}/verification`}>Cancel</Link>
          </Button>
        )}
        <Button icon="check_circle" busy={busy} busyLabel={verification ? 'Saving' : 'Posting'} onClick={save}>
          {verification ? 'Save and update Discord' : 'Create and post'}
        </Button>
      </div>
    </div>
  )
}
