import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { RacerVerification, VerifiedRacer } from '../../api/client'
import { fail, reply, USERS } from '../../test/fakeApi'
import { currentPath, main, renderApp } from '../../test/renderApp'
import { check } from './VerificationForm'
import { countsText, formatDate, recheckText, roleText } from './VerificationSection'

const GUILD = '100000000000000001'
const SERVER = {
  id: GUILD,
  name: 'Dev Server',
  text_channels: [
    { id: '300', name: 'get-verified' },
    { id: '301', name: 'mod-log' },
  ],
  voice_channels: [],
  roles: [
    { id: '77', name: 'Verified Racer', position: 2, assignable: true },
    { id: '78', name: 'Mystery Racer', position: 1, assignable: true },
    { id: '79', name: 'Moderators', position: 5, assignable: false },
  ],
}

const verification = (overrides: Partial<RacerVerification> = {}): RacerVerification => ({
  id: 3,
  guild_id: GUILD,
  role_id: '77',
  role_name: 'Verified Racer',
  channel_id: '300',
  channel_name: 'get-verified',
  message_id: '900',
  racetime_categories: ['alttpr'],
  use_alttpr_ladder: true,
  minimum_races: 5,
  time_period_days: 365,
  reverify_period_days: 90,
  revoke_ineligible: true,
  audit_channel_id: '301',
  audit_channel_name: 'mod-log',
  requirement: '5 races in 365 days',
  verified_count: 2,
  ...overrides,
})

const racer = (overrides: Partial<VerifiedRacer> = {}): VerifiedRacer => ({
  id: 1,
  discord_user_id: '200',
  name: 'Linkle',
  racetime_id: 'abc',
  racetime_url: 'https://racetime.gg/user/abc/',
  race_count: 37,
  verified_at: '2026-01-01T00:00:00Z',
  last_checked: '2026-11-12T00:00:00Z',
  next_check: '2027-02-10T00:00:00Z',
  status: 'verified',
  ...overrides,
})

const LIST = `GET /api/v1/servers/${GUILD}/racer-verifications`
const CATEGORIES = ['alttpr', 'smz3', 'smr']

function admin(routes: Record<string, unknown> = {}) {
  return {
    signedIn: USERS.alice,
    routes: {
      'GET /api/v1/servers': { servers: [{ id: GUILD, name: 'Dev Server' }] },
      [`GET /api/v1/servers/${GUILD}`]: SERVER,
      [LIST]: { verifications: [verification()], racetime_categories: CATEGORIES },
      'GET /api/v1/racer-verifications/3': verification(),
      'GET /api/v1/racer-verifications/3/racers': {
        racers: [
          racer(),
          racer({ id: 2, name: 'Slowpoke', race_count: 2, status: 'not_qualified', racetime_url: null, racetime_id: null }),
          racer({ id: 4, name: 'Overdue', status: 'due' }),
        ],
      },
      ...routes,
    },
  }
}

describe('labels', () => {
  it('describe a verification', () => {
    expect(roleText(verification())).toBe('@Verified Racer')
    expect(roleText(verification({ role_name: null }))).toBe('@deleted role')
    expect(countsText(verification())).toBe('alttpr, ALTTPR Ladder')
    expect(recheckText(verification())).toBe('Every 90 days')
    expect(recheckText(verification({ reverify_period_days: 1 }))).toBe('Every day')
    expect(recheckText(verification({ reverify_period_days: null }))).toBe('Off')
    expect(formatDate(null)).toBe('–')
    expect(formatDate('2026-11-12T12:00:00Z')).toMatch(/2026/)
  })

  it('check the form before saving', () => {
    const ok = { roleId: '77', channelId: '300', categories: ['alttpr'], ladder: false, minimum: '5', period: '365', recheck: '', revoke: false, auditChannelId: '' }
    expect(check(ok)).toBeUndefined()
    expect(check({ ...ok, roleId: '' })).toMatch(/role/)
    expect(check({ ...ok, channelId: '' })).toMatch(/channel/)
    expect(check({ ...ok, categories: [] })).toMatch(/at least one/)
    expect(check({ ...ok, categories: [], ladder: true })).toBeUndefined()
    expect(check({ ...ok, minimum: '0' })).toMatch(/Races needed/)
    expect(check({ ...ok, period: 'x' })).toMatch(/counting period/)
    expect(check({ ...ok, recheck: '0' })).toMatch(/Recheck/)
    expect(check({ ...ok, recheck: '30' })).toBeUndefined()
  })
})

describe('the verification list', () => {
  it('lists each role with what it needs', async () => {
    const { user } = renderApp(`/servers/${GUILD}/verification`, admin())
    const link = await screen.findByRole('link', { name: '@Verified Racer' })
    expect(link.getAttribute('href')).toBe(`/servers/${GUILD}/verification/3`)
    expect(main().textContent).toContain('5 races in 365 days')
    expect(main().textContent).toContain('Every 90 days')
    expect(main().textContent).toContain('removes the role')
    await user.click(screen.getByRole('link', { name: 'New verification' }))
    expect(currentPath()).toBe(`/servers/${GUILD}/verification/new`)
  })

  it('says when there is a problem and reposts from the row menu', async () => {
    const { user, api } = renderApp(
      `/servers/${GUILD}/verification`,
      admin({
        [LIST]: { verifications: [verification({ message_id: null })], racetime_categories: CATEGORIES },
        'POST /api/v1/racer-verifications/3/repost': verification(),
      }),
    )
    expect(await screen.findByText(/isn't posted/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'More for @Verified Racer' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Repost in Discord' }))
    await waitFor(() => expect(api.callsTo('POST /api/v1/racer-verifications/3/repost')).toHaveLength(1))
    await waitFor(() => expect(api.callsTo(LIST)).toHaveLength(2))
  })

  it('shows the empty state', async () => {
    renderApp(`/servers/${GUILD}/verification`, admin({ [LIST]: { verifications: [], racetime_categories: CATEGORIES } }))
    expect(await screen.findByText('No racer verification yet')).toBeTruthy()
  })

  it('deletes after confirming, and shows a failure', async () => {
    const { user, api } = renderApp(
      `/servers/${GUILD}/verification`,
      admin({ 'DELETE /api/v1/racer-verifications/3': fail(403, 'Only administrators of that server can manage it here.') }),
    )
    await user.click(await screen.findByRole('button', { name: 'More for @Verified Racer' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Delete' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent).toContain('Nobody loses')
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Only administrators')
    expect(api.callsTo('DELETE /api/v1/racer-verifications/3')).toHaveLength(1)
  })
})

describe('a new verification', () => {
  it('posts the settings and opens the new page', async () => {
    const { user, api } = renderApp(
      `/servers/${GUILD}/verification/new`,
      admin({
        [LIST]: { verifications: [], racetime_categories: CATEGORIES },
        [`POST /api/v1/servers/${GUILD}/racer-verifications`]: reply(201, verification({ id: 8, verified_count: 0 })),
        'GET /api/v1/racer-verifications/8': verification({ id: 8, verified_count: 0 }),
        'GET /api/v1/racer-verifications/8/racers': { racers: [] },
      }),
    )
    const role = await screen.findByLabelText('Role to give')
    // Roles SahasrahBot can't give aren't offered.
    expect(within(role).queryByText('@Moderators')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Create and post' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Pick the role')

    await user.selectOptions(role, '77')
    await user.selectOptions(screen.getByLabelText('Post the Verify button in'), '300')
    await user.click(screen.getByRole('button', { name: 'smz3' }))
    await user.clear(screen.getByLabelText('Races needed'))
    await user.type(screen.getByLabelText('Races needed'), '5')
    const revoke = screen.getByRole('checkbox', { name: /Take the role away/ }) as HTMLInputElement
    expect(revoke.disabled).toBe(true)
    await user.type(screen.getByLabelText('Recheck every'), '90')
    await user.click(revoke)
    await user.selectOptions(screen.getByLabelText('Report changes in'), '301')
    await user.click(screen.getByRole('button', { name: 'Create and post' }))

    await waitFor(() => expect(currentPath()).toBe(`/servers/${GUILD}/verification/8`))
    expect(api.callsTo(`POST /api/v1/servers/${GUILD}/racer-verifications`)[0]!.body).toEqual({
      role_id: '77',
      channel_id: '300',
      racetime_categories: ['alttpr', 'smz3'],
      use_alttpr_ladder: false,
      minimum_races: 5,
      time_period_days: 365,
      reverify_period_days: 90,
      revoke_ineligible: true,
      audit_channel_id: '301',
    })
    expect(await screen.findByText(/Posted the Verify button/)).toBeTruthy()
    expect(await screen.findByText('Nobody has verified yet')).toBeTruthy()
  })

  it("doesn't offer roles that already have verification", async () => {
    renderApp(`/servers/${GUILD}/verification/new`, admin())
    const role = await screen.findByLabelText('Role to give')
    expect(within(role).queryByText('@Verified Racer')).toBeNull()
    expect(within(role).getByText('@Mystery Racer')).toBeTruthy()
  })
})

describe("a verification's page", () => {
  it('lists verified racers and filters them', async () => {
    const { user } = renderApp(`/servers/${GUILD}/verification/3`, admin())
    expect(await screen.findByRole('heading', { name: '@Verified Racer' })).toBeTruthy()
    expect(await screen.findByText('Linkle')).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'racetime.gg profile' })[0]!.getAttribute('href')).toBe('https://racetime.gg/user/abc/')
    expect(screen.getByRole('link', { name: 'Jump to the message' }).getAttribute('href')).toBe(
      `https://discord.com/channels/${GUILD}/300/900`,
    )
    await user.click(screen.getByRole('button', { name: /Doesn't qualify now/ }))
    expect(screen.queryByText('Linkle')).toBeNull()
    expect(screen.getByText('Slowpoke')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^All/ }))
    await user.type(screen.getByRole('searchbox', { name: 'Search by name' }), 'over')
    expect(screen.getByText('Overdue')).toBeTruthy()
    expect(screen.queryByText('Linkle')).toBeNull()
    await user.clear(screen.getByRole('searchbox', { name: 'Search by name' }))
    await user.type(screen.getByRole('searchbox', { name: 'Search by name' }), 'zzz')
    expect(screen.getByText('Nobody matches')).toBeTruthy()
  })

  it('rechecks a racer now', async () => {
    const { user, api } = renderApp(
      `/servers/${GUILD}/verification/3`,
      admin({ 'POST /api/v1/racer-verifications/3/racers/1/recheck': { racer: racer({ race_count: 40 }) } }),
    )
    await user.click(await screen.findByRole('button', { name: 'More for Linkle' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Recheck now' }))
    expect(await screen.findByText(/Rechecked Linkle: 40 races counted. Verified./)).toBeTruthy()
    expect(api.callsTo('POST /api/v1/racer-verifications/3/racers/1/recheck')).toHaveLength(1)
  })

  it('says when a recheck removed someone, and when it fails', async () => {
    const { user } = renderApp(
      `/servers/${GUILD}/verification/3`,
      admin({
        'POST /api/v1/racer-verifications/3/racers/1/recheck': { racer: null },
        'POST /api/v1/racer-verifications/3/racers/4/recheck': fail(400, 'racetime.gg is down.'),
      }),
    )
    await user.click(await screen.findByRole('button', { name: 'More for Linkle' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Recheck now' }))
    expect(await screen.findByText(/so they were removed/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'More for Overdue' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Recheck now' }))
    expect(await screen.findByText('racetime.gg is down.')).toBeTruthy()
  })

  it('removes a racer after confirming', async () => {
    const { user, api } = renderApp(`/servers/${GUILD}/verification/3`, admin({ 'DELETE /api/v1/racer-verifications/3/racers/1': reply(204) }))
    await user.click(await screen.findByRole('button', { name: 'More for Linkle' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Remove verification' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Remove' }))
    expect(await screen.findByText(/Removed Linkle and took the role away/)).toBeTruthy()
    expect(api.callsTo('DELETE /api/v1/racer-verifications/3/racers/1')).toHaveLength(1)
  })

  it('edits the settings', async () => {
    const { user, api } = renderApp(
      `/servers/${GUILD}/verification/3/settings`,
      admin({ 'PUT /api/v1/racer-verifications/3': verification({ minimum_races: 3, requirement: '3 races in 365 days' }) }),
    )
    const minimum = await screen.findByLabelText('Races needed')
    expect((minimum as HTMLInputElement).value).toBe('5')
    // Its own role is still offered.
    expect(within(screen.getByLabelText('Role to give')).getByText('@Verified Racer')).toBeTruthy()
    await user.clear(minimum)
    await user.type(minimum, '3')
    await user.clear(screen.getByLabelText('Recheck every'))
    await user.click(screen.getByRole('button', { name: 'Save and update Discord' }))
    await waitFor(() => expect(api.callsTo('PUT /api/v1/racer-verifications/3')).toHaveLength(1))
    expect(api.callsTo('PUT /api/v1/racer-verifications/3')[0]!.body).toMatchObject({
      minimum_races: 3,
      reverify_period_days: null,
      revoke_ineligible: false,
    })
    expect(await screen.findByText(/Saved. The message in Discord is updated./)).toBeTruthy()
  })

  it('shows a save failure', async () => {
    const { user } = renderApp(
      `/servers/${GUILD}/verification/3/settings`,
      admin({ 'PUT /api/v1/racer-verifications/3': fail(400, "SahasrahBot can't post in that channel.") }),
    )
    await user.click(await screen.findByRole('button', { name: 'Save and update Discord' }))
    expect((await screen.findByRole('alert')).textContent).toContain("can't post in that channel")
  })

  it('reposts and deletes from the Actions menu', async () => {
    const { user, api } = renderApp(
      `/servers/${GUILD}/verification/3`,
      admin({ 'POST /api/v1/racer-verifications/3/repost': verification(), 'DELETE /api/v1/racer-verifications/3': reply(204) }),
    )
    await user.click(await screen.findByRole('button', { name: 'Actions' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Repost in Discord' }))
    expect(await screen.findByText(/Posted the Verify button again/)).toBeTruthy()
    expect(api.callsTo('POST /api/v1/racer-verifications/3/repost')).toHaveLength(1)

    await user.click(screen.getByRole('button', { name: 'Actions' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Delete verification' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(currentPath()).toBe(`/servers/${GUILD}/verification`))
    expect(await screen.findByText(/Deleted racer verification for @Verified Racer/)).toBeTruthy()
  })

  it('warns about a deleted role', async () => {
    renderApp(`/servers/${GUILD}/verification/3`, admin({ 'GET /api/v1/racer-verifications/3': verification({ role_name: null }) }))
    expect(await screen.findByText(/The role was deleted/)).toBeTruthy()
  })
})
