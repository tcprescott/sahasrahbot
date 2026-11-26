import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { RoleMenu, RoleMenuServerOptions } from '../api/client'
import { browser } from '../lib/browser'
import { fail, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'

const GUILD = '600000000000000001'
const LIST = `/servers/${GUILD}/role-menus`

const SERVER: RoleMenuServerOptions = {
  channels: [
    { id: '700', name: '#roles' },
    { id: '701', name: '#general' },
  ],
  roles: [
    { id: '800', name: '@Racer', assignable: true },
    { id: '801', name: '@Voter', assignable: true },
    { id: '802', name: '@Moderator', assignable: false },
  ],
  emojis: [{ id: '900', name: '<:triforce:900>' }],
}

const menu = (overrides: Partial<RoleMenu> = {}): RoleMenu => ({
  id: 1,
  guild_id: GUILD,
  guild_name: 'ALTTPR Racing',
  channel_id: '700',
  channel_name: '#roles',
  message_id: '1000',
  title: 'Pings',
  description: 'Pick what to be pinged for.',
  style: 'buttons',
  posted_by_bot: true,
  single_choice: false,
  options: [
    { id: 11, role_id: '800', role_name: '@Racer', label: 'Races', emoji: '🏁', description: null },
    { id: 12, role_id: '801', role_name: '@Voter', label: 'Votes', emoji: null, description: 'Election news' },
  ],
  problems: [],
  ...overrides,
})

const LEGACY = menu({ id: 2, title: 'Racer role', style: 'reactions', posted_by_bot: false, options: [menu().options[0]!] })

function open(path: string, routes: Record<string, unknown> = {}) {
  return renderApp(path, {
    signedIn: USERS.alice,
    routes: {
      'GET /api/v1/role-menus': { menus: [menu(), LEGACY] },
      [`GET /api/v1/role-menus/servers/${GUILD}`]: SERVER,
      'GET /api/v1/role-menus/1': menu(),
      'GET /api/v1/role-menus/2': LEGACY,
      ...routes,
    },
  })
}

describe('Role menu list', () => {
  it("lists the server's menus with their channel, roles and style", async () => {
    const { api } = open(LIST)
    const page = main()
    expect(await within(page).findByRole('link', { name: 'Pings' })).toBeTruthy()
    expect(within(page).getByRole('link', { name: 'Racer role' })).toBeTruthy()
    expect(within(page).getAllByText('Buttons').length).toBeGreaterThan(0)
    expect(within(page).getAllByText('Reactions').length).toBeGreaterThan(0)
    expect(within(page).getAllByLabelText('Races, Votes').length).toBeGreaterThan(0)
    expect(api.callsTo('GET /api/v1/role-menus')[0]?.query.get('guild_id')).toBe(GUILD)
    expect(within(page).getByRole('link', { name: 'New role menu' }).getAttribute('href')).toBe(`${LIST}/new`)
  })

  it('shows what will stop a menu working', async () => {
    open(LIST, { 'GET /api/v1/role-menus': { menus: [menu({ problems: ['SahasrahBot can’t see #roles.', 'Another one.'] })] } })
    expect(await screen.findByText(/SahasrahBot can’t see #roles\./)).toBeTruthy()
    expect(screen.getByText(/\+1 more/)).toBeTruthy()
  })

  it('says when there are none, with labels for menus without emoji', async () => {
    open(LIST, { 'GET /api/v1/role-menus': { menus: [] } })
    expect(await screen.findByText('No role menus yet')).toBeTruthy()
  })

  it('reposts and deletes after asking', async () => {
    const { api, user } = open(LIST, {
      'POST /api/v1/role-menus/1/repost': menu(),
      'DELETE /api/v1/role-menus/1': {},
    })
    await screen.findByRole('link', { name: 'Pings' })
    await user.click(screen.getAllByRole('button', { name: 'More for Pings' })[0]!)
    await user.click(await screen.findByRole('menuitem', { name: 'Repost in Discord' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Repost' }))
    expect(await screen.findByText('“Pings” is reposted.')).toBeTruthy()
    expect(api.callsTo('POST /api/v1/role-menus/1/repost')).toHaveLength(1)

    await user.click(screen.getAllByRole('button', { name: 'More for Pings' })[0]!)
    await user.click(await screen.findByRole('menuitem', { name: 'Delete' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Delete' }))
    expect(await screen.findByText('“Pings” is deleted.')).toBeTruthy()
    expect(api.callsTo('DELETE /api/v1/role-menus/1')).toHaveLength(1)
  })

  it('jumps to the message in Discord', async () => {
    const opened = vi.spyOn(browser, 'open').mockImplementation(() => {})
    const { user } = open(LIST)
    await screen.findByRole('link', { name: 'Pings' })
    await user.click(screen.getAllByRole('button', { name: 'More for Pings' })[0]!)
    await user.click(await screen.findByRole('menuitem', { name: 'Jump to the message' }))
    expect(opened).toHaveBeenCalledWith(`https://discord.com/channels/${GUILD}/700/1000`)
  })

  it('shows an action that failed', async () => {
    const { user } = open(LIST, { 'POST /api/v1/role-menus/1/repost': fail(400, 'SahasrahBot can’t post in #roles.') })
    await screen.findByRole('link', { name: 'Pings' })
    await user.click(screen.getAllByRole('button', { name: 'More for Pings' })[0]!)
    await user.click(await screen.findByRole('menuitem', { name: 'Repost in Discord' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Repost' }))
    expect(await screen.findByText('SahasrahBot can’t post in #roles.')).toBeTruthy()
  })
})

describe('Role menu editor', () => {
  it('makes a new menu in the channel it was opened for, and posts it', async () => {
    const { api, user } = open(`${LIST}/new?channel=701`, {
      'POST /api/v1/role-menus': menu({ id: 5, title: 'Pronouns' }),
      'GET /api/v1/role-menus/5': menu({ id: 5, title: 'Pronouns' }),
    })
    expect(await screen.findByRole('heading', { level: 1, name: 'New role menu' })).toBeTruthy()
    await waitFor(() => expect((screen.getByLabelText('Channel') as HTMLSelectElement).value).toBe('701'))
    await user.type(screen.getByLabelText('Title'), 'Pronouns')
    await user.click(screen.getByLabelText(/^Dropdown/))
    await user.click(screen.getByLabelText(/only one role/))

    await user.click(screen.getByRole('button', { name: 'Add role' }))
    const dialog = await screen.findByRole('dialog')
    const roleSelect = within(dialog).getByLabelText('Role') as HTMLSelectElement
    expect((within(roleSelect).getByRole('option', { name: /@Moderator/ }) as HTMLOptionElement).disabled).toBe(true)
    await user.click(within(dialog).getByRole('button', { name: 'Add' }))
    expect(within(dialog).getByText('Pick a role.')).toBeTruthy()
    await user.selectOptions(roleSelect, '801')
    expect((within(dialog).getByLabelText('Label') as HTMLInputElement).value).toBe('Voter')
    await user.click(within(dialog).getByRole('button', { name: '<:triforce:900>' }))
    await user.type(within(dialog).getByLabelText('Description (optional)'), 'Votes')
    await user.click(within(dialog).getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())

    const preview = screen.getByRole('figure', { name: 'Preview in Discord' })
    expect(within(preview).getByText('Pronouns')).toBeTruthy()
    expect(within(preview).getByText('Pick a role to add or remove')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Create and post' }))
    await waitFor(() => expect(currentPath()).toBe(`${LIST}/5`))
    expect(api.callsTo('POST /api/v1/role-menus')[0]?.body).toEqual({
      guild_id: GUILD,
      channel_id: '701',
      title: 'Pronouns',
      description: null,
      style: 'dropdown',
      single_choice: true,
      options: [{ id: null, role_id: '801', label: 'Voter', emoji: '<:triforce:900>', description: 'Votes' }],
    })
    expect(await screen.findByText('“Pronouns” is posted in Discord.')).toBeTruthy()
  })

  it('needs an emoji for every role on a reactions menu', async () => {
    const { user } = open(`${LIST}/new`)
    await screen.findByRole('heading', { level: 1, name: 'New role menu' })
    await user.click(screen.getByLabelText(/^Reactions/))
    await user.click(screen.getByRole('button', { name: 'Add role' }))
    const dialog = await screen.findByRole('dialog')
    await user.selectOptions(within(dialog).getByLabelText('Role'), '800')
    await user.click(within(dialog).getByRole('button', { name: 'Add' }))
    expect(within(dialog).getByText('Reaction menus need an emoji for every role.')).toBeTruthy()
  })

  it('shows what the server says is wrong when posting fails', async () => {
    const { user } = open(`${LIST}/new`, { 'POST /api/v1/role-menus': fail(400, 'Give the menu at least one role.') })
    await screen.findByRole('heading', { level: 1, name: 'New role menu' })
    await waitFor(() => expect((screen.getByLabelText('Channel') as HTMLSelectElement).value).toBe('700'))
    await user.click(screen.getByRole('button', { name: 'Create and post' }))
    expect(await screen.findByText('Give the menu at least one role.')).toBeTruthy()
  })

  it('edits, reorders and removes roles, then saves', async () => {
    const { api, user } = open(`${LIST}/1`, { 'PUT /api/v1/role-menus/1': menu() })
    expect(await screen.findByRole('heading', { level: 1, name: 'Pings' })).toBeTruthy()
    expect(screen.getByText('Roles (2 of 25)')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Move Votes up' }))
    await user.click(screen.getByRole('button', { name: 'More for Races' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Edit' }))
    const dialog = await screen.findByRole('dialog', { name: 'Edit role' })
    const label = within(dialog).getByLabelText('Label')
    await user.clear(label)
    await user.type(label, 'Race pings')
    await user.click(within(dialog).getByRole('button', { name: 'Done' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())

    await user.click(screen.getByRole('button', { name: 'Save and update Discord' }))
    expect(await screen.findByText('Saved. The menu in Discord is updated.')).toBeTruthy()
    const body = api.callsTo('PUT /api/v1/role-menus/1')[0]?.body as { options: { id: number; label: string }[] }
    expect(body.options.map((o) => [o.id, o.label])).toEqual([
      [12, 'Votes'],
      [11, 'Race pings'],
    ])

    await user.click(screen.getByRole('button', { name: 'More for Votes' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Remove' }))
    expect(screen.getByText('Roles (1 of 25)')).toBeTruthy()
  })

  it('keeps a menu on someone else’s message to reactions, and offers a repost', async () => {
    const { api, user } = open(`${LIST}/2`, { 'POST /api/v1/role-menus/2/repost': { ...LEGACY, posted_by_bot: true } })
    expect(await screen.findByRole('heading', { level: 1, name: 'Racer role' })).toBeTruthy()
    expect(screen.getByText(/didn't post, so it can only use reactions/)).toBeTruthy()
    expect((screen.getByLabelText(/^Buttons/) as HTMLInputElement).disabled).toBe(true)
    expect((screen.getByLabelText('Channel') as HTMLSelectElement).disabled).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Repost as SahasrahBot' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Repost' }))
    expect(await screen.findByText('Reposted. SahasrahBot posted the menu as a new message.')).toBeTruthy()
    expect(api.callsTo('POST /api/v1/role-menus/2/repost')).toHaveLength(1)
  })

  it('lists problems and deletes from the Actions menu', async () => {
    const { api, user } = open(`${LIST}/1`, {
      'GET /api/v1/role-menus/1': menu({ problems: ['One.', 'Two.'] }),
      'DELETE /api/v1/role-menus/1': {},
    })
    expect(await screen.findByText('One.')).toBeTruthy()
    expect(screen.getByText('Two.')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /Actions/ }))
    await user.click(await screen.findByRole('menuitem', { name: 'Delete menu' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(currentPath()).toBe(LIST))
    expect(api.callsTo('DELETE /api/v1/role-menus/1')).toHaveLength(1)
    expect(await screen.findByText('“Pings” is deleted.')).toBeTruthy()
  })

  it('says when the menu is gone', async () => {
    open(`${LIST}/9`, { 'GET /api/v1/role-menus/9': fail(404, 'There’s no role menu 9.') })
    expect(await screen.findByText('There’s no role menu 9.')).toBeTruthy()
  })
})

describe('Role menus signed out', () => {
  it('sends the visitor to sign in', async () => {
    const { assigned } = renderApp(`${LIST}/1`, { routes: {} })
    await waitFor(() => expect(assigned[0]).toContain('/login/'))
  })
})
