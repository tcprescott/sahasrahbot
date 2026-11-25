import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Namespace, Preset } from '../api/client'
import { fail, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'
import { findYamlEditor } from '../test/yamlEditor'

const NS = '/api/v1/presets/namespaces/alice'
const PRESET = `${NS}/alttpr/open_fast`

const summary = (randomizer: string, name: string, generated_count = 0) => ({
  namespace: 'alice',
  randomizer,
  name,
  modified: '2026-11-01T12:00:00Z',
  generated_count,
})

const namespace = (overrides: Partial<Namespace> = {}): Namespace => ({
  name: 'alice',
  can_edit: true,
  presets: [summary('alttpr', 'open_fast', 3), summary('alttpr', 'keysanity'), summary('smz3', 'normal')],
  ...overrides,
})

const preset = (overrides: Partial<Preset> = {}): Preset => ({
  ...summary('alttpr', 'open_fast', 1),
  content: 'settings:\n  mode: open\n',
  can_edit: true,
  ...overrides,
})

const rowNames = () =>
  within(screen.getByRole('table'))
    .getAllByRole('rowheader')
    .map((cell) => cell.textContent)

describe('all namespaces', () => {
  const routes = {
    'GET /api/v1/presets/namespaces': {
      namespaces: [
        { name: 'alice', preset_count: 3 },
        { name: 'Synack', preset_count: 12 },
      ],
    },
  }

  it('lists every namespace with its count', async () => {
    renderApp('/presets', { routes })
    expect(await screen.findByRole('link', { name: 'alice' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Synack' }).getAttribute('href')).toBe('/presets/manage/Synack')
    expect(rowNames()).toEqual(['alice', 'Synack'])
  })

  it('filters by name, ignoring case', async () => {
    const { user } = renderApp('/presets', { routes })
    await user.type(await screen.findByRole('searchbox', { name: 'Find a namespace' }), 'SYN')
    expect(rowNames()).toEqual(['Synack'])
    await user.clear(screen.getByRole('searchbox'))
    await user.type(screen.getByRole('searchbox'), 'zzz ')
    expect(screen.getByText('No namespace matches "zzz"')).toBeTruthy()
  })

  it('lays the list out as cards on a phone', async () => {
    renderApp('/presets', { routes, phone: true })
    const cards = await screen.findByRole('list', { name: 'Preset namespaces' })
    expect(within(cards).getAllByRole('listitem')).toHaveLength(2)
    expect(screen.queryByRole('table')).toBeNull()
    expect(within(cards).getAllByText('Presets')).toHaveLength(2)
  })
})

describe('my presets', () => {
  it("opens the signed-in user's namespace", async () => {
    renderApp('/presets/me', {
      signedIn: USERS.alice,
      routes: { 'GET /api/v1/presets/mine': { namespace: 'alice' }, [`GET ${NS}`]: namespace() },
    })
    await waitFor(() => expect(currentPath()).toBe('/presets/manage/alice'))
    expect(await screen.findByRole('heading', { level: 1, name: "alice's presets" })).toBeTruthy()
  })
})

describe('one namespace', () => {
  it('lists presets with download links and filters by randomizer', async () => {
    const { user } = renderApp('/presets/manage/alice', { routes: { [`GET ${NS}`]: namespace() } })
    await screen.findByRole('table')
    expect(rowNames()).toEqual(['open_fast', 'keysanity', 'normal'])
    expect(screen.getByRole('link', { name: 'open_fast' }).getAttribute('href')).toBe('/presets/manage/alice/alttpr/open_fast')
    expect(screen.getByRole('link', { name: 'Download normal' }).getAttribute('href')).toBe('/presets/download/alice/smz3/normal')

    const chips = screen.getByRole('group', { name: 'Randomizer' })
    expect(within(chips).getAllByRole('button').map((b) => b.textContent)).toEqual(['All 3', 'alttpr 2', 'smz3 1'])
    await user.click(within(chips).getByRole('button', { name: 'smz3 1' }))
    expect(currentPath()).toBe('/presets/manage/alice/smz3')
    expect(rowNames()).toEqual(['normal'])
    expect(within(chips).getByRole('button', { name: 'smz3 1' }).getAttribute('aria-pressed')).toBe('true')
    await user.click(within(chips).getByRole('button', { name: 'All 3' }))
    expect(currentPath()).toBe('/presets/manage/alice')
  })

  it("hides the randomizer filter when there's only one", async () => {
    renderApp('/presets/manage/alice', { routes: { [`GET ${NS}`]: namespace({ presets: [summary('alttpr', 'a')] }) } })
    await screen.findByRole('table')
    expect(screen.queryByRole('group', { name: 'Randomizer' })).toBeNull()
  })

  it("gives someone else's namespace no New preset and no row menu", async () => {
    renderApp('/presets/manage/alice', { routes: { [`GET ${NS}`]: namespace({ can_edit: false }) } })
    await screen.findByRole('table')
    expect(screen.queryByRole('link', { name: 'New preset' })).toBeNull()
    expect(screen.queryByRole('button', { name: /More for/ })).toBeNull()
  })

  it.each([
    [true, "You haven't made any presets yet"],
    [false, 'No presets here yet'],
  ])('an empty namespace (can_edit %s) says "%s"', async (can_edit, title) => {
    renderApp('/presets/manage/alice', { routes: { [`GET ${NS}`]: namespace({ can_edit, presets: [] }) } })
    expect(await screen.findByText(title)).toBeTruthy()
  })

  it('says when the namespace does not exist', async () => {
    renderApp('/presets/manage/alice', { routes: { [`GET ${NS}`]: fail(404, '') } })
    expect(await screen.findByText("There's no namespace called alice.")).toBeTruthy()
  })

  it('opens a preset for editing from its row menu', async () => {
    const { user } = renderApp('/presets/manage/alice', { routes: { [`GET ${NS}`]: namespace(), [`GET ${PRESET}`]: preset() } })
    await user.click(await screen.findByRole('button', { name: 'More for open_fast' }))
    await user.click(screen.getByRole('menuitem', { name: 'Edit' }))
    expect(currentPath()).toBe('/presets/manage/alice/alttpr/open_fast?edit=1')
    expect(await screen.findByRole('textbox', { name: 'Preset YAML' })).toBeTruthy()
  })

  it('deletes a preset after confirming, then reloads the list', async () => {
    const { user, api } = renderApp('/presets/manage/alice', {
      routes: { [`GET ${NS}`]: namespace(), [`DELETE ${PRESET}`]: { ok: true } },
    })
    await user.click(await screen.findByRole('button', { name: 'More for open_fast' }))
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }))
    const dialog = screen.getByRole('dialog', { name: 'Delete open_fast?' })
    expect(dialog.textContent).toContain('alice/open_fast (alttpr) stops working in Discord')
    api.on(`GET ${NS}`, namespace({ presets: [summary('smz3', 'normal')] }))
    await user.click(within(dialog).getByRole('button', { name: 'Delete preset' }))

    await waitFor(() => expect(rowNames()).toEqual(['normal']))
    expect(api.callsTo(`DELETE ${PRESET}`)).toHaveLength(1)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('shows why a delete failed', async () => {
    const { user } = renderApp('/presets/manage/alice', {
      routes: { [`GET ${NS}`]: namespace(), [`DELETE ${PRESET}`]: fail(403, 'That preset is not yours.') },
    })
    await user.click(await screen.findByRole('button', { name: 'More for open_fast' }))
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }))
    await user.click(screen.getByRole('button', { name: 'Delete preset' }))
    expect((await screen.findByRole('alert')).textContent).toContain('That preset is not yours.')
    expect(rowNames()).toContain('open_fast')
  })
})

describe('one preset', () => {
  const path = '/presets/manage/alice/alttpr/open_fast'

  it('shows the YAML and how often it was rolled', async () => {
    renderApp(path, { routes: { [`GET ${PRESET}`]: preset({ can_edit: false }) } })
    expect(await screen.findByRole('heading', { level: 1, name: 'alice/open_fast' })).toBeTruthy()
    expect(main().textContent).toContain('rolled 1 time')
    expect(main().querySelector('pre')?.textContent).toBe('settings:\n  mode: open\n')
    expect(screen.getByRole('link', { name: 'Download' }).getAttribute('href')).toBe('/presets/download/alice/alttpr/open_fast')
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
  })

  it('says "times" for any count but one', async () => {
    renderApp(path, { routes: { [`GET ${PRESET}`]: preset({ generated_count: 0 }) } })
    await screen.findByRole('heading', { level: 1 })
    expect(main().textContent).toContain('rolled 0 times')
  })

  it('edits and saves the YAML', async () => {
    const { user, api } = renderApp(path, {
      routes: { [`GET ${PRESET}`]: preset(), [`PUT ${PRESET}`]: preset({ content: 'settings:\n  mode: inverted\n' }) },
    })
    await user.click(await screen.findByRole('button', { name: 'Edit' }))
    expect(currentPath()).toBe(`${path}?edit=1`)
    const save = screen.getByRole('button', { name: 'Save' })
    expect(save.hasAttribute('disabled')).toBe(true) // nothing changed yet

    const editor = await findYamlEditor()
    editor.replace('settings:\n  mode: inverted\n')
    api.on(`GET ${PRESET}`, preset({ content: 'settings:\n  mode: inverted\n' }))
    await user.click(save)

    await waitFor(() => expect(currentPath()).toBe(path))
    expect(api.callsTo(`PUT ${PRESET}`)[0]?.body).toEqual({ content: 'settings:\n  mode: inverted\n' })
    await waitFor(async () => expect((await findYamlEditor()).text()).toBe('settings:\n  mode: inverted\n'))
  })

  it('keeps the draft and shows the error when saving fails', async () => {
    const { user } = renderApp(`${path}?edit=1`, {
      routes: { [`GET ${PRESET}`]: preset(), [`PUT ${PRESET}`]: fail(400, 'That YAML has a syntax error on line 2.') },
    })
    const editor = await findYamlEditor()
    editor.moveTo()
    editor.type('oops: 1')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect((await screen.findByRole('alert')).textContent).toContain('syntax error on line 2')
    expect(editor.text()).toBe('settings:\n  mode: open\noops: 1')
    expect(currentPath()).toBe(`${path}?edit=1`)
  })

  it('throws the draft away on Cancel', async () => {
    const { user } = renderApp(`${path}?edit=1`, { routes: { [`GET ${PRESET}`]: preset() } })
    ;(await findYamlEditor()).type('junk')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(currentPath()).toBe(path)
    expect((await findYamlEditor()).text()).toBe('settings:\n  mode: open\n')
  })

  it('loads the YAML from a file', async () => {
    const { user } = renderApp(`${path}?edit=1`, { routes: { [`GET ${PRESET}`]: preset() } })
    const editor = await findYamlEditor()
    const input = main().querySelector<HTMLInputElement>('input[type=file]')!
    await user.upload(input, new File(['from: file\n'], 'mine.yaml', { type: 'text/yaml' }))
    await waitFor(() => expect(editor.text()).toBe('from: file\n'))
  })

  it('downloads from the Actions menu', async () => {
    const { user, assigned } = renderApp(path, { routes: { [`GET ${PRESET}`]: preset() } })
    await user.click(await screen.findByRole('button', { name: 'Actions' }))
    await user.click(screen.getByRole('menuitem', { name: 'Download' }))
    expect(assigned).toEqual(['/presets/download/alice/alttpr/open_fast'])
  })

  it('deletes after confirming and goes back to the namespace', async () => {
    const { user, api } = renderApp(path, {
      routes: { [`GET ${PRESET}`]: preset(), [`DELETE ${PRESET}`]: { ok: true }, [`GET ${NS}`]: namespace() },
    })
    await user.click(await screen.findByRole('button', { name: 'Actions' }))
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }))
    await user.click(screen.getByRole('button', { name: 'Delete preset' }))
    await waitFor(() => expect(currentPath()).toBe('/presets/manage/alice'))
    expect(api.callsTo(`DELETE ${PRESET}`)).toHaveLength(1)
  })

  it('test_known_issue: ?edit=1 on a preset you cannot edit hides the Download button', async () => {
    // The header's actions are hidden whenever ?edit=1 is set, but the editor only
    // shows for can_edit, so a non-owner with an old edit link gets the YAML and no Download.
    renderApp(`${path}?edit=1`, { routes: { [`GET ${PRESET}`]: preset({ can_edit: false }) } })
    await screen.findByRole('heading', { level: 1 })
    expect((await findYamlEditor()).view.state.readOnly).toBe(true)
    expect(screen.queryByRole('link', { name: 'Download' })).toBeNull()
  })
})

describe('new preset', () => {
  const routes = {
    [`GET ${NS}`]: namespace(),
    'GET /api/v1/presets/randomizers': { randomizers: ['alttpr', 'sm', 'smz3'] },
  }

  it("refuses someone else's namespace", async () => {
    renderApp('/presets/alice/create', { signedIn: USERS.bob, routes: { ...routes, [`GET ${NS}`]: namespace({ can_edit: false }) } })
    expect(await screen.findByText("This isn't your namespace")).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Go to your presets' }).getAttribute('href')).toBe('/presets/me')
  })

  it('needs a valid name and some YAML before it saves', async () => {
    const { user } = renderApp('/presets/alice/create', { signedIn: USERS.alice, routes })
    const name = await screen.findByRole('textbox', { name: 'Name' })
    const save = screen.getByRole('button', { name: 'Save preset' })
    expect(save.hasAttribute('disabled')).toBe(true)

    await user.type(name, 'has space')
    await user.type(screen.getByRole('textbox', { name: 'Preset YAML' }), 'a: 1')
    expect(name.getAttribute('aria-invalid')).toBe('true')
    expect(save.hasAttribute('disabled')).toBe(true)

    await user.clear(name)
    await user.type(name, 'good_name')
    expect(name.getAttribute('aria-invalid')).toBe('false')
    expect(main().textContent).toContain('Rolled as alice/good_name')
    expect(save.hasAttribute('disabled')).toBe(false)
  })

  it('saves under the chosen randomizer and opens the new preset', async () => {
    const saved = preset({ randomizer: 'smz3', name: 'mine' })
    const { user, api } = renderApp('/presets/alice/create', {
      signedIn: USERS.alice,
      routes: { ...routes, [`PUT ${NS}/smz3/mine`]: saved, [`GET ${NS}/smz3/mine`]: saved },
    })
    expect(within(await screen.findByRole('combobox', { name: 'Randomizer' })).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'alttpr',
      'sm',
      'smz3',
    ])
    await user.type(screen.getByRole('textbox', { name: 'Name' }), 'mine')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Randomizer' }), 'smz3')
    ;(await findYamlEditor()).type('a: 1')
    await user.click(screen.getByRole('button', { name: 'Save preset' }))

    await waitFor(() => expect(currentPath()).toBe('/presets/manage/alice/smz3/mine'))
    expect(api.callsTo(`PUT ${NS}/smz3/mine`)[0]?.body).toEqual({ content: 'a: 1' })
  })

  it('shows why saving failed', async () => {
    const { user } = renderApp('/presets/alice/create', {
      signedIn: USERS.alice,
      routes: { ...routes, [`PUT ${NS}/alttpr/mine`]: fail(400, "That isn't valid YAML.") },
    })
    await user.type(await screen.findByRole('textbox', { name: 'Name' }), 'mine')
    await user.type(screen.getByRole('textbox', { name: 'Preset YAML' }), 'a: [[')
    await user.click(screen.getByRole('button', { name: 'Save preset' }))
    expect((await screen.findByRole('alert')).textContent).toContain("That isn't valid YAML.")
    expect(screen.getByRole('button', { name: 'Save preset' }).hasAttribute('disabled')).toBe(false)
  })

  it('goes back to the namespace on Cancel', async () => {
    const { user } = renderApp('/presets/alice/create', { signedIn: USERS.alice, routes })
    await user.click(await screen.findByRole('button', { name: 'Cancel' }))
    expect(currentPath()).toBe('/presets/manage/alice')
  })
})
