import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ServerDetail, ServerSettings } from '../api/client'
import { fail, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'
import { initials } from './initials'

const ID = '100000000000000001'
const SERVERS = {
  servers: [
    { id: ID, name: 'Dev Server' },
    { id: '200', name: 'other place' },
  ],
}
const DETAIL: ServerDetail = {
  id: ID,
  name: 'Dev Server',
  text_channels: [
    { id: '300', name: '#daily' },
    { id: '301', name: '#races' },
  ],
  voice_channels: [],
  roles: [],
}
const SETTINGS: ServerSettings = {
  daily_channels: [
    { name: 'daily', usable: true },
    { name: 'old-dailies', usable: false },
  ],
  holy_image_game: null,
  holy_image_fallback: 'z3r',
  holy_image_games: ['smz3', 'z3r'],
}

const admin = (routes: Record<string, unknown> = {}) => ({
  signedIn: USERS.alice,
  routes: {
    'GET /api/v1/elections/servers': SERVERS,
    'GET /api/v1/servers': SERVERS,
    [`GET /api/v1/servers/${ID}`]: DETAIL,
    [`GET /api/v1/servers/${ID}/settings`]: SETTINGS,
    ...routes,
  },
})

describe('initials', () => {
  it('takes the first letters of two words', () => {
    expect(initials('ALTTPR Racing Community')).toBe('AR')
    expect(initials('smz3')).toBe('S')
    expect(initials('  ')).toBe('?')
  })
})

describe('the Servers tab', () => {
  it('is shown to server admins and lists their servers', async () => {
    const { user } = renderApp('/', admin())
    const [rail] = screen.getAllByRole('navigation', { name: 'Main' })
    await user.click(await within(rail!).findByRole('link', { name: 'Servers' }))
    expect(currentPath()).toBe('/servers')
    await user.click(await screen.findByRole('link', { name: /Dev Server/ }))
    expect(currentPath()).toBe(`/servers/${ID}/settings`)
  })

  it('says when there is nothing to manage', async () => {
    renderApp('/servers', { signedIn: USERS.alice, routes: { 'GET /api/v1/servers': { servers: [] } } })
    expect(await screen.findByText('No servers to manage')).toBeTruthy()
  })
})

describe('a server page', () => {
  it('opens on Settings and switches servers', async () => {
    const { user } = renderApp(`/servers/${ID}`, admin())
    expect(await screen.findByRole('heading', { level: 1, name: 'Dev Server' })).toBeTruthy()
    expect(currentPath()).toBe(`/servers/${ID}/settings`)
    const tabs = screen.getByRole('navigation', { name: 'Server sections' })
    await waitFor(() => expect(within(tabs).getByRole('link', { name: 'Settings' }).className).toContain('active'))
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Switch server' }), '200')
    expect(currentPath()).toBe('/servers/200/settings')
  })

  it('explains a server it cannot open', async () => {
    renderApp(`/servers/${ID}/settings`, admin({ [`GET /api/v1/servers/${ID}`]: fail(403, 'Only administrators of that server can manage it here.') }))
    expect(await screen.findByText('Only administrators of that server can manage it here.')).toBeTruthy()
  })
})

describe('server settings', () => {
  it('flags channels the bot cannot post in, and saves changes', async () => {
    const { user, api } = renderApp(
      `/servers/${ID}/settings`,
      admin({ [`PUT /api/v1/servers/${ID}/settings`]: { ...SETTINGS, daily_channels: [{ name: 'daily', usable: true }, { name: 'races', usable: true }], holy_image_game: 'smz3' } }),
    )
    const chips = await screen.findByRole('list', { name: 'Daily challenge channels' })
    expect(within(chips).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['#daily', '#old-dailies'])
    expect(main().textContent).toContain("#old-dailies no longer exists or SahasrahBot can't post there")
    const save = screen.getByRole('button', { name: 'Save settings' }) as HTMLButtonElement
    expect(save.disabled).toBe(true)

    await user.click(screen.getByRole('button', { name: 'Remove #old-dailies' }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Announce the ALTTPR daily challenge in' }), 'races')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Default game for /holyimage' }), 'smz3')
    expect(screen.getByText('Unsaved changes')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    expect(await screen.findByText('Settings saved.')).toBeTruthy()
    expect(api.callsTo(`PUT /api/v1/servers/${ID}/settings`)[0]!.body).toEqual({ daily_channels: ['daily', 'races'], holy_image_game: 'smz3' })
    expect(screen.queryByText('Unsaved changes')).toBeNull()
  })

  it('discards changes and shows save errors', async () => {
    const { user } = renderApp(`/servers/${ID}/settings`, admin({ [`PUT /api/v1/servers/${ID}/settings`]: fail(400, "SahasrahBot can't post in #races.") }))
    await screen.findByRole('list', { name: 'Daily challenge channels' })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Default game for /holyimage' }), 'smz3')
    await user.click(screen.getByRole('button', { name: 'Discard' }))
    expect((screen.getByRole('combobox', { name: 'Default game for /holyimage' }) as HTMLSelectElement).value).toBe('')

    await user.click(screen.getByRole('button', { name: 'Remove #daily' }))
    await user.click(screen.getByRole('button', { name: 'Save settings' }))
    expect(await screen.findByText("SahasrahBot can't post in #races.")).toBeTruthy()
  })

  it('keeps a saved game the holy image site no longer lists', async () => {
    renderApp(`/servers/${ID}/settings`, admin({ [`GET /api/v1/servers/${ID}/settings`]: { ...SETTINGS, holy_image_game: 'gone', holy_image_games: [] } }))
    const select = (await screen.findByRole('combobox', { name: 'Default game for /holyimage' })) as HTMLSelectElement
    await waitFor(() => expect(select.value).toBe('gone'))
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual(['z3r (the default)', 'gone'])
  })
})
