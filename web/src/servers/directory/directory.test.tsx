import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { fail, USERS } from '../../test/fakeApi'
import { main, renderApp } from '../../test/renderApp'
import { messagesFor, type ServerDirectory } from './DirectorySection'

const GUILD = '100000000000000001'
const BASE = `/api/v1/servers/${GUILD}/directory`
const SERVER = {
  id: GUILD,
  name: 'Dev Server',
  text_channels: [
    { id: '300', name: 'partner-servers' },
    { id: '301', name: 'other-servers' },
  ],
  voice_channels: [],
  roles: [],
}

const directory = (overrides: Partial<ServerDirectory> = {}): ServerDirectory => ({
  guild_id: GUILD,
  servers_per_message: 10,
  last_posted_at: '2026-11-20T12:00:00Z',
  unposted_changes: false,
  categories: [
    {
      id: 1,
      title: 'Randomizers',
      description: 'Main hubs',
      channel_id: '300',
      servers: [
        { id: 11, invite_code: 'alttpr', description: 'ALTTPR' },
        { id: 12, invite_code: 'smz3', description: 'SMZ3' },
      ],
    },
    { id: 2, title: 'Speedrunning', description: null, channel_id: '301', servers: [] },
  ],
  ...overrides,
})

const open = (routes: Record<string, unknown> = {}, phone = false) =>
  renderApp(`/servers/${GUILD}/directory`, {
    signedIn: USERS.alice,
    phone,
    routes: { [`GET /api/v1/servers/${GUILD}`]: SERVER, [`GET ${BASE}`]: directory(), ...routes },
  })

describe('server directory', () => {
  it('shows each category, its servers and a preview of the channel', async () => {
    open()
    const randomizers = await screen.findByRole('list', { name: 'Servers in Randomizers' })
    expect(within(randomizers).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      expect.stringContaining('ALTTPRdiscord.gg/alttpr'),
      expect.stringContaining('SMZ3discord.gg/smz3'),
    ])
    expect((main()).textContent).toContain('Posted in #partner-servers · Main hubs')
    expect((main()).textContent).toContain('No servers yet.')
    const preview = screen.getByRole('region', { name: 'Preview in Discord' })
    expect((preview).textContent).toContain('Randomizers')
    expect((preview).textContent).toContain('SMZ3: https://discord.gg/smz3')
    expect(screen.queryByText(/Discord still shows the old list/)).toBeNull()
  })

  it('reorders servers and categories', async () => {
    const { api, user } = open({
      [`PUT ${BASE}/categories/1/order`]: directory(),
      [`PUT ${BASE}/order`]: directory({ unposted_changes: true }),
    })
    await user.click(await screen.findByRole('button', { name: 'Move SMZ3 up' }))
    await waitFor(() => expect(api.callsTo(`PUT ${BASE}/categories/1/order`)[0]?.body).toEqual({ ids: [12, 11] }))
    expect((screen.getByRole('button', { name: 'Move ALTTPR up' }) as HTMLButtonElement).disabled).toBe(true)

    await user.click(screen.getByRole('button', { name: 'Move Speedrunning up' }))
    await waitFor(() => expect(api.callsTo(`PUT ${BASE}/order`)[0]?.body).toEqual({ ids: [2, 1] }))
    expect(await screen.findByText(/You've made changes since the list was last posted/)).toBeTruthy()
  })

  it('adds a server after checking its invite', async () => {
    const added = directory()
    added.categories[1]!.servers.push({ id: 13, invite_code: 'zelda', description: 'Zelda Randomizer' })
    const { api, user } = open({
      [`GET ${BASE}/invite`]: { code: 'zelda', server_name: 'Zelda Randomizer', member_count: 4210, expires_at: null },
      [`POST ${BASE}/categories/2/servers`]: added,
    })
    const buttons = await screen.findAllByRole('button', { name: 'Add server' })
    await user.click(buttons[1]!)
    const dialog = await screen.findByRole('dialog', { name: 'Add a server to Speedrunning' })
    await user.type(within(dialog).getByLabelText('Invite link'), 'https://discord.gg/zelda')
    await user.click(within(dialog).getByLabelText('Text shown in Discord'))
    expect((await within(dialog).findByRole('status')).textContent).toContain('Invite works · never expires · 4,210 members')
    expect(api.callsTo(`GET ${BASE}/invite`)[0]?.query.get('invite')).toBe('https://discord.gg/zelda')
    expect((within(dialog).getByLabelText('Text shown in Discord') as HTMLInputElement | HTMLSelectElement).value).toBe('Zelda Randomizer')

    await user.click(within(dialog).getByRole('button', { name: 'Add server' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(api.callsTo(`POST ${BASE}/categories/2/servers`)[0]?.body).toEqual({
      invite: 'https://discord.gg/zelda',
      description: 'Zelda Randomizer',
    })
    expect((screen.getByRole('list', { name: 'Servers in Speedrunning' })).textContent).toContain('Zelda Randomizer')
  })

  it('shows why an invite or a save was refused', async () => {
    const { user } = open({
      [`GET ${BASE}/invite`]: fail(400, "That invite doesn't work: it may have expired or been deleted."),
      [`POST ${BASE}/categories/1/servers`]: fail(400, "That invite doesn't work: it may have expired or been deleted."),
    })
    await user.click((await screen.findAllByRole('button', { name: 'Add server' }))[0]!)
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Add server' }))
    expect(within(dialog).getByText('Paste the server’s invite link.')).toBeTruthy()

    await user.type(within(dialog).getByLabelText('Invite link'), 'expired')
    await user.type(within(dialog).getByLabelText('Text shown in Discord'), 'Old')
    expect(await within(dialog).findByText(/That invite doesn't work/)).toBeTruthy()
    await user.click(within(dialog).getByRole('button', { name: 'Add server' }))
    expect(await screen.findAllByText(/That invite doesn't work/)).toHaveLength(2) // the dialog's and the page's
  })

  it('makes, edits and deletes categories', async () => {
    const { api, user } = open({
      [`POST ${BASE}/categories`]: directory(),
      [`PUT ${BASE}/categories/1`]: directory(),
      [`DELETE ${BASE}/categories/1`]: directory({ categories: [] }),
    })
    await user.click(await screen.findByRole('button', { name: 'Actions' }))
    await user.click(await screen.findByRole('menuitem', { name: 'New category' }))
    let dialog = await screen.findByRole('dialog', { name: 'New category' })
    await user.type(within(dialog).getByLabelText('Title'), 'Tournaments')
    await user.click(within(dialog).getByRole('button', { name: 'Add category' }))
    expect(within(dialog).getByText('Pick the channel it’s posted in.')).toBeTruthy()
    await user.selectOptions(within(dialog).getByLabelText('Channel'), '#other-servers')
    await user.click(within(dialog).getByRole('button', { name: 'Add category' }))
    await waitFor(() =>
      expect(api.callsTo(`POST ${BASE}/categories`)[0]?.body).toEqual({ title: 'Tournaments', description: null, channel_id: '301' }),
    )

    await user.click(screen.getByRole('button', { name: 'More for Randomizers' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Edit category' }))
    dialog = await screen.findByRole('dialog', { name: 'Edit category' })
    expect((within(dialog).getByLabelText('Title') as HTMLInputElement | HTMLSelectElement).value).toBe('Randomizers')
    await user.clear(within(dialog).getByLabelText('Note (optional)'))
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(api.callsTo(`PUT ${BASE}/categories/1`)[0]?.body).toEqual({ title: 'Randomizers', description: null, channel_id: '300' }),
    )

    await user.click(screen.getByRole('button', { name: 'More for Randomizers' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Delete category' }))
    dialog = await screen.findByRole('dialog', { name: 'Delete this category?' })
    expect((dialog).textContent).toContain('“Randomizers” and the 2 servers in it are deleted.')
    await user.click(within(dialog).getByRole('button', { name: 'Delete category' }))
    expect(await screen.findByText('No categories yet')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Post to Discord' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('edits, moves and removes a server', async () => {
    const { api, user } = open({
      [`PUT ${BASE}/servers/12`]: directory(),
      [`DELETE ${BASE}/servers/12`]: directory(),
    })
    await user.click(await screen.findByRole('button', { name: 'More for SMZ3' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Edit' }))
    let dialog = await screen.findByRole('dialog', { name: 'Edit server' })
    expect((within(dialog).getByLabelText('Invite link') as HTMLInputElement | HTMLSelectElement).value).toBe('https://discord.gg/smz3')
    await user.selectOptions(within(dialog).getByLabelText('Category'), 'Speedrunning')
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(api.callsTo(`PUT ${BASE}/servers/12`)[0]?.body).toEqual({
        invite: 'https://discord.gg/smz3',
        description: 'SMZ3',
        category_id: 2,
      }),
    )

    await user.click(screen.getByRole('button', { name: 'More for SMZ3' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Remove' }))
    dialog = await screen.findByRole('dialog', { name: 'Remove this server?' })
    await user.click(within(dialog).getByRole('button', { name: 'Remove server' }))
    await waitFor(() => expect(api.callsTo(`DELETE ${BASE}/servers/12`)).toHaveLength(1))
  })

  it('posts to Discord after saying which channels are cleared', async () => {
    const { api, user } = open({
      [`GET ${BASE}`]: directory({ unposted_changes: true }),
      [`POST ${BASE}/post`]: { messages: 1, channel_ids: ['300', '301'] },
    })
    expect(await screen.findByText(/Discord still shows the old list/)).toBeTruthy()
    await user.click(screen.getAllByRole('button', { name: 'Post to Discord' })[0]!)
    const dialog = await screen.findByRole('dialog', { name: 'Post the server list to Discord?' })
    expect((dialog).textContent).toContain('#partner-servers: Randomizers (2)')
    expect((dialog).textContent).toContain('#other-servers: Speedrunning (0)')
    api.on(`GET ${BASE}`, directory())
    await user.click(within(dialog).getByRole('button', { name: 'Post 2 categories' }))
    expect(await screen.findByText('Posted 1 message to Discord.')).toBeTruthy()
    expect(api.callsTo(`POST ${BASE}/post`)).toHaveLength(1)
    expect(screen.queryByText(/Discord still shows the old list/)).toBeNull()
  })

  it('says when posting fails', async () => {
    const { user } = open({
      [`POST ${BASE}/post`]: fail(400, 'SahasrahBot needs Manage Messages in #partner-servers.'),
    })
    await user.click(await screen.findByRole('button', { name: 'Post to Discord' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Post 2 categories' }))
    expect(await screen.findByText('SahasrahBot needs Manage Messages in #partner-servers.')).toBeTruthy()
  })

  it('moves a category from its menu on a phone', async () => {
    const { api, user } = open({ [`PUT ${BASE}/order`]: directory() }, true)
    await user.click(await screen.findByRole('button', { name: 'More for Randomizers' }))
    expect(screen.queryByRole('menuitem', { name: 'Move up' })).toBeNull()
    await user.click(await screen.findByRole('menuitem', { name: 'Move down' }))
    await waitFor(() => expect(api.callsTo(`PUT ${BASE}/order`)[0]?.body).toEqual({ ids: [2, 1] }))
  })

  it('switches the preview between channels', async () => {
    const { user } = open()
    const preview = await screen.findByRole('region', { name: 'Preview in Discord' })
    await user.click(within(preview).getByRole('button', { name: '#other-servers' }))
    expect((preview).textContent).toContain('Nothing is posted here')
  })
})

describe('messagesFor', () => {
  it('splits a category into parts of servers_per_message', () => {
    const servers = Array.from({ length: 5 }, (_, i) => ({ id: i, invite_code: `s${i}`, description: `S${i}` }))
    const dir = directory({
      servers_per_message: 2,
      categories: [{ id: 1, title: 'Big', description: null, channel_id: '300', servers }],
    })
    expect(messagesFor(dir, '300').map((m) => [m.title, m.servers.length])).toEqual([
      ['Big - Part 1', 2],
      ['Big - Part 2', 2],
      ['Big - Part 3', 1],
    ])
    expect(messagesFor(dir, '999')).toEqual([])
  })
})
