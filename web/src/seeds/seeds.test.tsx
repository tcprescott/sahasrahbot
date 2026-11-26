import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { fail, reply, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'
import { hashFrom } from './rolling'

const PRESET = '/api/v1/presets/namespaces/alice/alttpr/open_fast'
const preset = (overrides: Record<string, unknown> = {}) => ({
  namespace: 'alice',
  randomizer: 'alttpr',
  name: 'open_fast',
  modified: '2026-11-01T12:00:00Z',
  generated_count: 1,
  content: 'settings:\n  mode: open\n',
  can_edit: true,
  ...overrides,
})
const seed = (overrides: Record<string, unknown> = {}) => ({
  randomizer: 'alttpr',
  preset: 'alice/open_fast',
  url: 'https://alttpr.com/h/abc123',
  hash: 'abc123',
  file_select_code: ['Bow', 'Hookshot', 'Bombos', 'Mushroom', 'Lamp'],
  spoiler_url: null,
  custom_instructions: null,
  ...overrides,
})
const BUILT_IN = {
  'GET /api/v1/seeds/presets/alttpr': { randomizer: 'alttpr', presets: ['open', 'standard'] },
  'GET /api/v1/seeds/presets/alttprmystery': { randomizer: 'alttprmystery', presets: ['weighted'] },
  'GET /api/v1/seeds/presets/sm': { randomizer: 'sm', presets: ['casual_full'] },
  'GET /api/v1/seeds/presets/smz3': { randomizer: 'smz3', presets: ['normal'] },
}

describe('hashFrom', () => {
  it.each([
    ['abc123', 'abc123'],
    ['  abc123 ', 'abc123'],
    ['https://alttpr.com/h/abc123', 'abc123'],
    ['https://samus.link/seed/xyz/', 'xyz'],
    ['https://alttpr.com/', ''],
  ])('%s gives %s', (text, hash) => expect(hashFrom(text)).toBe(hash))
})

describe('rolling from a preset page', () => {
  const path = '/presets/manage/alice/alttpr/open_fast'

  it('rolls with the chosen options and shows the seed in the dialog', async () => {
    const { user, api } = renderApp(path, {
      signedIn: USERS.alice,
      routes: { [`GET ${PRESET}`]: preset(), 'POST /api/v1/seeds': reply(201, seed()) },
    })
    await user.click(await screen.findByRole('button', { name: 'Roll a seed' }))
    const dialog = screen.getByRole('dialog', { name: 'Roll alice/open_fast' })
    await user.click(within(dialog).getByRole('switch', { name: /Race seed/ }))
    await user.click(within(dialog).getByRole('switch', { name: /Hints/ }))
    await user.click(within(dialog).getByRole('switch', { name: /Allow quickswap/ }))
    await user.selectOptions(within(dialog).getByRole('combobox'), 'beeta')
    await user.click(within(dialog).getByRole('button', { name: 'Roll' }))

    const result = await screen.findByRole('dialog', { name: 'Your seed' })
    expect(api.callsTo('POST /api/v1/seeds')[0]?.body).toEqual({
      randomizer: 'alttpr',
      preset: 'alice/open_fast',
      race: true,
      hints: true,
      allow_quickswap: false,
      branch: 'beeta',
    })
    expect(within(result).getByRole('link', { name: 'https://alttpr.com/h/abc123' })).toBeTruthy()
    expect(within(within(result).getByRole('list', { name: 'File select code' })).getAllByRole('listitem')).toHaveLength(5)
    expect(within(result).getByRole('link', { name: /Open seed/ }).getAttribute('href')).toBe('https://alttpr.com/h/abc123')
    await waitFor(() => expect(api.callsTo(`GET ${PRESET}`)).toHaveLength(2)) // the count goes up

    await user.click(within(result).getByRole('button', { name: 'Roll another' }))
    expect(screen.getByRole('dialog', { name: 'Roll alice/open_fast' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('copies the seed link', async () => {
    const { user } = renderApp(path, {
      signedIn: USERS.alice,
      routes: { [`GET ${PRESET}`]: preset(), 'POST /api/v1/seeds': reply(201, seed()) },
    })
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    await user.click(await screen.findByRole('button', { name: 'Roll a seed' }))
    await user.click(screen.getByRole('button', { name: 'Roll' }))
    await user.click(await screen.findByRole('button', { name: 'Copy link' }))
    expect(writeText).toHaveBeenCalledWith('https://alttpr.com/h/abc123')
    expect(await screen.findByRole('button', { name: 'Copied' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Done' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('shows why a roll failed and keeps the options', async () => {
    const { user } = renderApp(path, {
      signedIn: USERS.alice,
      routes: { [`GET ${PRESET}`]: preset(), 'POST /api/v1/seeds': fail(400, 'The randomizer could not generate that game.') },
    })
    await user.click(await screen.findByRole('button', { name: 'Roll a seed' }))
    await user.click(screen.getByRole('button', { name: 'Roll' }))
    expect((await screen.findByRole('alert')).textContent).toContain('could not generate')
    expect(screen.getByRole('dialog', { name: 'Roll alice/open_fast' })).toBeTruthy()
  })

  it('sends a signed-out visitor to sign in first', async () => {
    const { user, assigned } = renderApp(path, { routes: { [`GET ${PRESET}`]: preset({ can_edit: false }) } })
    await user.click(await screen.findByRole('button', { name: 'Roll a seed' }))
    expect(assigned).toEqual([`/login/?next=${encodeURIComponent(path)}`])
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('offers only the options that apply to SMZ3', async () => {
    const smz3 = '/api/v1/presets/namespaces/alice/smz3/open_fast'
    const { user, api } = renderApp('/presets/manage/alice/smz3/open_fast', {
      signedIn: USERS.alice,
      routes: {
        [`GET ${smz3}`]: preset({ randomizer: 'smz3' }),
        'POST /api/v1/seeds': reply(201, seed({ randomizer: 'smz3', spoiler_url: 'https://samus.link/spoiler/x' })),
      },
    })
    await user.click(await screen.findByRole('button', { name: 'Roll a seed' }))
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).queryByRole('switch', { name: /Hints/ })).toBeNull()
    expect(within(dialog).queryByRole('combobox')).toBeNull()
    await user.click(within(dialog).getByRole('switch', { name: /Spoiler race/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Roll' }))
    expect((await screen.findByRole('link', { name: 'Open the spoiler log' })).getAttribute('href')).toBe('https://samus.link/spoiler/x')
    expect(api.callsTo('POST /api/v1/seeds')[0]?.body).toEqual({
      randomizer: 'smz3',
      preset: 'alice/open_fast',
      race: false,
      spoiler_race: true,
    })
  })
})

describe('the Seeds page', () => {
  it('is a tab', async () => {
    renderApp('/seeds', { signedIn: USERS.alice, routes: BUILT_IN })
    const [rail] = screen.getAllByRole('navigation', { name: 'Main' })
    expect(within(rail!).getByRole('link', { name: 'Seeds' }).getAttribute('aria-current')).toBe('page')
    expect(await screen.findByRole('heading', { level: 1, name: 'Seeds' })).toBeTruthy()
  })

  it('rolls a built-in preset for the chosen randomizer', async () => {
    const { user, api } = renderApp('/seeds', {
      signedIn: USERS.alice,
      routes: {
        ...BUILT_IN,
        'POST /api/v1/seeds': reply(201, seed({ randomizer: 'alttprmystery', preset: 'weighted', file_select_code: null, custom_instructions: 'Good luck!' })),
      },
    })
    await user.click(await screen.findByRole('button', { name: 'Mystery' }))
    await waitFor(() => expect(main().querySelector('datalist option[value="weighted"]')).toBeTruthy())
    expect(screen.queryByRole('switch', { name: /Hints/ })).toBeNull()
    await user.type(screen.getByLabelText('Preset'), 'weighted')
    await user.click(screen.getByRole('switch', { name: /Race seed/ }))
    await user.click(screen.getByRole('button', { name: 'Roll' }))
    expect(await screen.findByText('Good luck!')).toBeTruthy()
    expect(api.callsTo('POST /api/v1/seeds')[0]?.body).toEqual({
      randomizer: 'alttprmystery',
      preset: 'weighted',
      race: true,
      allow_quickswap: true,
    })
  })

  it('rolls Super Metroid with only the race option', async () => {
    const { user, api } = renderApp('/seeds', {
      signedIn: USERS.alice,
      routes: { ...BUILT_IN, 'POST /api/v1/seeds': fail(404, "There's no sm preset called nope.") },
    })
    await user.click(await screen.findByRole('button', { name: 'Super Metroid' }))
    expect(screen.getAllByRole('switch')).toHaveLength(1)
    await user.type(screen.getByLabelText('Preset'), 'nope')
    await user.click(screen.getByRole('button', { name: 'Roll' }))
    expect((await screen.findByRole('alert')).textContent).toContain('no sm preset called nope')
    expect(api.callsTo('POST /api/v1/seeds')[0]?.body).toEqual({ randomizer: 'sm', preset: 'nope', race: false })
  })

  it('looks up a seed from a pasted link, at its own address', async () => {
    const { user } = renderApp('/seeds', {
      signedIn: USERS.alice,
      routes: {
        ...BUILT_IN,
        'GET /api/v1/seeds/abc123': {
          hash: 'abc123',
          randomizer: 'alttpr',
          kind: 'preset',
          preset: 'open',
          url: 'https://alttpr.com/h/abc123',
          rolled_at: '2026-11-20T15:42:00Z',
        },
      },
    })
    await user.type(await screen.findByLabelText('Seed hash or link'), 'https://alttpr.com/h/abc123')
    await user.click(screen.getByRole('button', { name: 'Look up' }))
    expect(currentPath()).toBe('/seeds/abc123')
    const found = (await screen.findByRole('heading', { name: 'abc123' })).closest('section')!
    expect(within(found).getByText('preset')).toBeTruthy()
    expect(within(found).getByText('open')).toBeTruthy()
    expect(within(found).getByRole('link', { name: /Open seed/ }).getAttribute('href')).toBe('https://alttpr.com/h/abc123')
  })

  it("says when SahasrahBot didn't roll a seed", async () => {
    renderApp('/seeds/zzz', {
      signedIn: USERS.alice,
      routes: { ...BUILT_IN, 'GET /api/v1/seeds/zzz': fail(404, "SahasrahBot didn't roll a seed with the hash zzz.") },
    })
    expect(await screen.findByText(/didn't roll a seed with the hash zzz/)).toBeTruthy()
    expect((screen.getByLabelText('Seed hash or link') as HTMLInputElement).value).toBe('zzz')
  })

  it('shows what little was recorded about an old seed', async () => {
    renderApp('/seeds/old', {
      signedIn: USERS.alice,
      routes: { ...BUILT_IN, 'GET /api/v1/seeds/old': { hash: 'old', randomizer: null, kind: null, preset: null, url: null, rolled_at: null } },
    })
    expect(await screen.findAllByText('Not recorded')).toHaveLength(2)
    expect(screen.queryByRole('link', { name: /Open seed/ })).toBeNull()
  })

  it('asks a signed-out visitor to sign in', async () => {
    const { api } = renderApp('/seeds/abc123', { routes: BUILT_IN })
    expect((await within(main()).findByRole('link', { name: 'Sign in' })).getAttribute('href')).toBe('/login/?next=%2Fseeds%2Fabc123')
    expect(screen.getByRole('button', { name: 'Roll' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: 'Look up' }).hasAttribute('disabled')).toBe(true)
    expect(api.callsTo('GET /api/v1/seeds/abc123')).toHaveLength(0)
  })
})
