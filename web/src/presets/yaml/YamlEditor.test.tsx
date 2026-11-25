import { currentCompletions, startCompletion } from '@codemirror/autocomplete'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fakeApi } from '../../test/fakeApi'
import { findYamlEditor } from '../../test/yamlEditor'
import { YamlCode, YamlField } from '../YamlField'
import { clearHints } from './hintsCache'

const HINTS = 'GET /api/v1/presets/randomizers/alttpr/hints'

function Harness({ initial = '', onProblem }: Readonly<{ initial?: string; onProblem?: (p: string | null) => void }>) {
  const [value, setValue] = useState(initial)
  return (
    <>
      <YamlField value={value} onChange={setValue} onProblem={onProblem} randomizer="alttpr" />
      <output data-testid="value">{value}</output>
    </>
  )
}

const status = () => document.querySelector('.yaml-box__status')!

afterEach(() => clearHints())

describe('YamlField', () => {
  it('shows a plain text box until the editor has loaded, which already works', () => {
    fakeApi()
    const onChange = vi.fn()
    render(<YamlField value="a: 1" onChange={onChange} />)
    const plain = screen.getByRole<HTMLTextAreaElement>('textbox', { name: 'Preset YAML' })
    expect(plain.tagName).toBe('TEXTAREA')
    fireEvent.change(plain, { target: { value: 'a: 2' } })
    expect(onChange).toHaveBeenCalledWith('a: 2')
  })

  it('says the YAML is valid, or how to start when empty', async () => {
    fakeApi()
    render(<Harness />)
    const editor = await findYamlEditor()
    expect(status().textContent).toContain('Type or paste the preset, or load a file.')
    editor.type('settings:\n  mode: open')
    expect(status().textContent).toContain('Valid YAML')
    expect(status().textContent).toContain('Ln 2, Col 13')
    expect(screen.getByTestId('value').textContent).toBe('settings:\n  mode: open')
  })

  it('marks the first problem, tells the page, and goes to its line', async () => {
    fakeApi()
    const onProblem = vi.fn()
    render(<Harness initial={'settings:\n  goal: ganon\n'} onProblem={onProblem} />)
    const editor = await findYamlEditor()
    expect(onProblem).toHaveBeenLastCalledWith(null)

    editor.replace('settings:\n  mode open\n  goal: ganon\n')
    const message = 'Line 2: a key here is missing its colon, or the line is indented wrongly.'
    expect(status().textContent).toContain(message)
    expect(onProblem).toHaveBeenLastCalledWith(message)

    editor.moveTo()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Go to line' }))
    expect(editor.view.state.selection.main.head).toBe(12)
  })

  it('wraps lines, folds everything, and goes full screen until Escape', async () => {
    fakeApi()
    const user = userEvent.setup()
    render(<Harness initial={'settings:\n  goal: ganon\n'} />)
    const editor = await findYamlEditor()

    await user.click(screen.getByRole('button', { name: 'Wrap lines' }))
    expect(screen.getByRole('button', { name: 'Wrap lines' }).getAttribute('aria-pressed')).toBe('true')
    expect(editor.view.contentDOM.classList.contains('cm-lineWrapping')).toBe(true)

    await user.click(screen.getByRole('button', { name: 'Fold all' }))
    await user.click(screen.getByRole('button', { name: 'Unfold all' }))
    expect(screen.getByRole('button', { name: 'Fold all' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Full screen' }))
    expect(screen.getByRole('dialog', { name: 'Preset YAML' })).toBeTruthy()
    expect(document.body.classList.contains('yaml-full-open')).toBe(true)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.body.classList.contains('yaml-full-open')).toBe(false)

    await user.click(screen.getByRole('button', { name: 'Full screen' }))
    await user.click(screen.getByRole('button', { name: 'Exit full screen' }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('loads a file into the editor', async () => {
    fakeApi()
    render(<Harness initial="old: 1" />)
    const editor = await findYamlEditor()
    await userEvent.setup().upload(document.querySelector<HTMLInputElement>('input[type=file]')!, new File(['new: 2\n'], 'p.yaml'))
    await waitFor(() => expect(editor.text()).toBe('new: 2\n'))
  })

  it("suggests the randomizer's keys and values, fetched once", async () => {
    const api = fakeApi({
      [HINTS]: {
        hints: [
          { path: [], key: 'settings', count: 3, values: [] },
          { path: ['settings'], key: 'goal', count: 3, values: ['ganon', 'dungeons'] },
          { path: ['settings'], key: 'glitches', count: 1, values: [] },
        ],
      },
    })
    render(<Harness initial={'settings:\n  g'} />)
    const editor = await findYamlEditor()
    await waitFor(() => expect(api.callsTo(HINTS)).toHaveLength(1))
    editor.moveTo()

    const suggested = async () => {
      act(() => void startCompletion(editor.view))
      await waitFor(() => expect(currentCompletions(editor.view.state).length).toBeGreaterThan(0))
      return currentCompletions(editor.view.state).map((c) => [c.label, c.detail])
    }
    expect(await suggested()).toEqual([
      ['goal', 'in 3 presets'],
      ['glitches', 'in 1 preset'],
    ])
    editor.type('oal: ')
    expect((await suggested()).map(([label]) => label)).toEqual(['ganon', 'dungeons'])
  })

  it('offers no suggestions when they cannot be fetched, and asks again next time', async () => {
    const api = fakeApi()
    const { unmount } = render(<Harness initial={'settings:\n  g'} />)
    const editor = await findYamlEditor()
    await waitFor(() => expect(api.callsTo(HINTS)).toHaveLength(1))
    editor.moveTo()
    act(() => void startCompletion(editor.view))
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(currentCompletions(editor.view.state)).toEqual([])
    unmount()
    render(<Harness />)
    await findYamlEditor()
    await waitFor(() => expect(api.callsTo(HINTS)).toHaveLength(2))
  })
})

describe('YamlCode', () => {
  it('shows the YAML read-only', async () => {
    fakeApi()
    render(<YamlCode value={'settings:\n  mode: open\n'} />)
    const view = await findYamlEditor()
    expect(view.text()).toBe('settings:\n  mode: open\n')
    expect(view.view.state.readOnly).toBe(true)
  })
})
