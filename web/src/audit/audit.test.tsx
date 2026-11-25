import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { AuditEntry, AuditOptions } from '../api/client'
import { fail, USERS } from '../test/fakeApi'
import { main, renderApp } from '../test/renderApp'
import { describeDetails, whenLabel } from './AuditScreen'

const OPTIONS: AuditOptions = {
  scopes: [
    { key: 'mine', label: 'My activity' },
    { key: '600', label: 'ALTTPR Racing' },
    { key: 'all', label: 'Everything' },
  ],
  areas: [
    { key: 'elections', label: 'Elections' },
    { key: 'server', label: 'Server settings and roles' },
  ],
}

const entry = (overrides: Partial<AuditEntry> = {}): AuditEntry => ({
  id: 10,
  created_at: '2026-11-24T20:00:00Z',
  action: 'server_setting.changed',
  label: 'Changed a server setting',
  area: 'server',
  actor_id: '81',
  actor_name: 'Gwen',
  via: 'discord',
  via_label: 'Discord',
  via_detail: '/config set',
  guild_id: '600',
  guild_name: 'ALTTPR Racing',
  target: 'DailyChannel',
  details: { changes: { DailyChannel: ['#races', '#daily-races'] } },
  ...overrides,
})

const SYSTEM = entry({ id: 9, action: 'election.closed', label: 'Closed an election', actor_id: null, actor_name: null, via: 'system', via_label: 'SahasrahBot', via_detail: null, target: 'Vote', details: {} })

function open(routes: Record<string, unknown> = {}, path = '/audit') {
  return renderApp(path, {
    signedIn: USERS.alice,
    routes: {
      'GET /api/v1/audit/options': OPTIONS,
      'GET /api/v1/audit': { entries: [entry(), SYSTEM], next_before: null },
      ...routes,
    },
  })
}

describe('Audit log page', () => {
  it("opens on the first server you run and lists its entries", async () => {
    const { api } = open()
    expect(await screen.findByRole('heading', { level: 1, name: 'Audit log' })).toBeTruthy()
    const page = main()
    expect(await within(page).findByText('Changed a server setting')).toBeTruthy()
    expect(within(page).getByText('Gwen')).toBeTruthy()
    expect(within(page).getAllByText('SahasrahBot').length).toBeGreaterThan(0)
    expect(within(page).getByText('· /config set')).toBeTruthy()
    expect(api.callsTo('GET /api/v1/audit')[0]?.query.get('scope')).toBe('600')
    expect((within(page).getByLabelText('Showing') as HTMLSelectElement).value).toBe('600')
  })

  it('filters by scope, area and search', async () => {
    const { api, user } = open()
    await screen.findByText('Changed a server setting')
    await user.selectOptions(screen.getByLabelText('Showing'), 'all')
    await waitFor(() => expect(api.callsTo('GET /api/v1/audit').at(-1)?.query.get('scope')).toBe('all'))
    await user.selectOptions(screen.getByLabelText('Area'), 'elections')
    await waitFor(() => expect(api.callsTo('GET /api/v1/audit').at(-1)?.query.get('area')).toBe('elections'))
    await user.type(screen.getByRole('textbox', { name: 'Search the audit log' }), 'gwen{Enter}')
    await waitFor(() => expect(api.callsTo('GET /api/v1/audit').at(-1)?.query.get('q')).toBe('gwen'))
  })

  it('loads older entries', async () => {
    const { api, user } = open({
      'GET /api/v1/audit': (call: { query: URLSearchParams }) =>
        call.query.get('before') ? { entries: [entry({ id: 3, target: 'Older one' })], next_before: null } : { entries: [entry()], next_before: 10 },
    })
    await user.click(await screen.findByRole('button', { name: 'Show older' }))
    expect(await screen.findByText('Older one')).toBeTruthy()
    expect(screen.getByText('DailyChannel')).toBeTruthy()
    expect(api.callsTo('GET /api/v1/audit').at(-1)?.query.get('before')).toBe('10')
    expect(screen.queryByRole('button', { name: 'Show older' })).toBeNull()
  })

  it('opens an entry with its change, and filters to that person', async () => {
    const { api, user } = open()
    await user.click(await screen.findByRole('button', { name: 'Changed a server setting: DailyChannel' }))
    const sheet = await screen.findByRole('dialog')
    expect(within(sheet).getByText('#races')).toBeTruthy()
    expect(within(sheet).getByText('#daily-races')).toBeTruthy()
    expect(within(sheet).getByText('server_setting.changed')).toBeTruthy()
    await user.click(within(sheet).getByRole('button', { name: 'More by Gwen' }))
    await waitFor(() => expect(api.callsTo('GET /api/v1/audit').at(-1)?.query.get('actor')).toBe('81'))
    expect(await screen.findByText('Only showing what Gwen did.')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Show everyone' }))
    await waitFor(() => expect(api.callsTo('GET /api/v1/audit').at(-1)?.query.get('actor')).toBeNull())
  })

  it('exports what is shown as CSV', async () => {
    const { assigned, user } = open({}, '/audit?scope=mine&area=elections')
    await user.click(await screen.findByRole('button', { name: 'Export CSV' }))
    expect(assigned).toEqual(['/api/v1/audit/export?scope=mine&area=elections'])
  })

  it('says when there is nothing, and shows errors', async () => {
    open({ 'GET /api/v1/audit': { entries: [], next_before: null } })
    expect(await screen.findByText('Nothing here yet')).toBeTruthy()
  })

  it('shows a refusal', async () => {
    const { user, api } = open({ 'GET /api/v1/audit': fail(403, 'You can only see the audit log of servers you administer.') })
    expect(await screen.findByText('You can only see the audit log of servers you administer.')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(api.callsTo('GET /api/v1/audit')).toHaveLength(2))
  })

  it('is linked from the Me page', async () => {
    renderApp('/me', {
      signedIn: USERS.alice,
      routes: { 'GET /api/v1/me': { user: USERS.alice, racetime_linked: false, racetime_id: null, preset_namespace: null, moderated_triforce_pools: [] } },
    })
    expect((await screen.findByRole('link', { name: 'Audit log' })).getAttribute('href')).toBe('/audit')
  })
})

describe('audit helpers', () => {
  it('labels times relative to today', () => {
    const now = new Date(2026, 10, 24, 15, 0)
    expect(whenLabel(new Date(2026, 10, 24, 9, 5).toISOString(), now)).not.toContain(',')
    expect(whenLabel(new Date(2026, 10, 23, 9, 5).toISOString(), now)).toMatch(/^Yesterday, /)
    expect(whenLabel(new Date(2026, 9, 2, 9, 5).toISOString(), now)).not.toMatch(/2026/)
    expect(whenLabel(new Date(2025, 9, 2, 9, 5).toISOString(), now)).toMatch(/2025/)
  })

  it('turns details into changes and facts', () => {
    expect(describeDetails({ changes: { voter_role_id: [null, 5], title: 'x' }, pool: 'dev', winners: ['A', 'B'], ok: true, data: { a: 1 } })).toEqual({
      changes: [
        ['Voter role id', 'nothing', '5'],
        ['Title', 'nothing', 'x'],
      ],
      facts: [
        ['Pool', 'dev'],
        ['Winners', 'A, B'],
        ['Ok', 'yes'],
        ['Data', '{"a":1}'],
      ],
    })
  })
})
