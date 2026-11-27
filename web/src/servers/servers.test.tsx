import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ServerDetail, ServerSettings } from '../api/client'
import { fail, reply, USERS, type Call } from '../test/fakeApi'
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
  roles: [
    { id: '77', name: '@Mods', position: 2, assignable: true },
    { id: '78', name: '@Helpers', position: 1, assignable: true },
  ],
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
    [`GET /api/v1/servers/${ID}/inquiries`]: { inquiries: [] },
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

const INQUIRY = {
  message_id: '900',
  channel_id: '300',
  channel_name: '#daily',
  role_id: '77',
  role_name: '@Mods',
  created: '2026-11-26T12:00:00Z',
  jump_url: `https://discord.com/channels/${ID}/300/900`,
}

describe('inquiry buttons', () => {
  it('lists them, jumps to one and removes one', async () => {
    const { user, api, assigned } = renderApp(
      `/servers/${ID}/settings`,
      admin({
        [`GET /api/v1/servers/${ID}/inquiries`]: { inquiries: [INQUIRY, { ...INQUIRY, message_id: '901', channel_id: null, channel_name: null, role_name: null, created: null, jump_url: null }] },
        [`DELETE /api/v1/servers/${ID}/inquiries/900`]: reply(204),
      }),
    )
    const list = await screen.findByRole('list', { name: 'Inquiry buttons' })
    expect(within(list).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      expect.stringContaining('Opens a private thread with @Mods'),
      expect.stringContaining('Opens a private thread with a deleted role'),
    ])
    await user.click(screen.getByRole('button', { name: 'More for the button in #daily' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Jump to the message' }))
    expect(assigned).toEqual([INQUIRY.jump_url])

    await user.click(screen.getByRole('button', { name: 'More for the button in #daily' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Remove' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Remove' }))
    expect(await screen.findByText(/Inquiry button removed/)).toBeTruthy()
    expect(api.callsTo(`DELETE /api/v1/servers/${ID}/inquiries/900`)).toHaveLength(1)
  })

  it('says when there are none', async () => {
    renderApp(`/servers/${ID}/settings`, admin())
    expect(await screen.findByText(/No inquiry buttons yet/)).toBeTruthy()
  })

  it('posts one once every check passes', async () => {
    const { user, api } = renderApp(
      `/servers/${ID}/settings`,
      admin({
        [`POST /api/v1/servers/${ID}/inquiries/check`]: (call: Call) => ({
          checks:
            (call.body as { role_id: string }).role_id === '77'
              ? [{ ok: true, text: 'SahasrahBot can create private threads in #daily' }, { ok: false, text: '@everyone can send messages in #daily.' }]
              : [{ ok: true, text: 'All good' }],
        }),
        [`POST /api/v1/servers/${ID}/inquiries`]: INQUIRY,
      }),
    )
    await user.click(await screen.findByRole('button', { name: 'Post an inquiry button' }))
    const dialog = await screen.findByRole('dialog', { name: 'Post an inquiry button' })
    expect(await within(dialog).findByText('@everyone can send messages in #daily.')).toBeTruthy()
    const post = within(dialog).getByRole('button', { name: 'Post in #daily' }) as HTMLButtonElement
    expect(post.disabled).toBe(true)

    await user.selectOptions(within(dialog).getByRole('combobox', { name: 'Who answers' }), '78')
    expect(await within(dialog).findByText('All good')).toBeTruthy()
    await user.selectOptions(within(dialog).getByRole('combobox', { name: 'Channel' }), '301')
    await waitFor(() => expect((within(dialog).getByRole('button', { name: 'Post in #races' }) as HTMLButtonElement).disabled).toBe(false))
    await user.click(within(dialog).getByRole('button', { name: 'Post in #races' }))

    expect(await screen.findByText('Inquiry button posted in #daily.')).toBeTruthy()
    expect(api.callsTo(`POST /api/v1/servers/${ID}/inquiries`)[0]!.body).toEqual({ channel_id: '301', role_id: '78' })
  })

  it('shows why posting failed', async () => {
    const { user } = renderApp(
      `/servers/${ID}/settings`,
      admin({
        [`POST /api/v1/servers/${ID}/inquiries/check`]: { checks: [{ ok: true, text: 'Fine' }] },
        [`POST /api/v1/servers/${ID}/inquiries`]: fail(400, "SahasrahBot isn't allowed to post in that channel."),
      }),
    )
    await user.click(await screen.findByRole('button', { name: 'Post an inquiry button' }))
    const dialog = await screen.findByRole('dialog')
    await within(dialog).findByText('Fine')
    await user.click(within(dialog).getByRole('button', { name: 'Post in #daily' }))
    expect(await within(dialog).findByText("SahasrahBot isn't allowed to post in that channel.")).toBeTruthy()
  })
})
