import { describe, expect, it } from 'vitest'
import { spotAt, suggestionsFor, type Hint } from './hints'

/** Where `|` is in the text. */
function at(marked: string) {
  const pos = marked.indexOf('|')
  return spotAt(marked.replace('|', ''), pos)
}

const HINTS: Hint[] = [
  { path: [], key: 'settings', count: 9, values: [] },
  { path: [], key: 'description', count: 8, values: [] },
  { path: ['settings'], key: 'mode', count: 5, values: ['open', 'standard'] },
  { path: ['settings'], key: 'goal', count: 7, values: ['ganon', 'dungeons'] },
  { path: ['settings'], key: 'eq', count: 2, values: ['PegasusBoots'] },
  { path: ['settings'], key: 'crystals', count: 6, values: [] },
  { path: ['settings', 'crystals'], key: 'ganon', count: 1, values: ["'7'"] },
  { path: ['settings', 'list'], key: 'x', count: 2, values: [] },
]

describe('spotAt', () => {
  it('knows a top-level key', () => {
    expect(at('sett|')).toEqual({ kind: 'key', path: [], from: 0 })
  })

  it('finds the keys above, skipping siblings, blank lines and comments', () => {
    const text = 'settings:\n  goal: ganon\n\n  # crystals next\n  crystals:\n    tower: "7"\n    gan|'
    expect(at(text)).toEqual({ kind: 'key', path: ['settings', 'crystals'], from: text.indexOf('|') - 3 })
  })

  it('knows a value, quoted keys included', () => {
    expect(at('settings:\n  mode: op|')).toEqual({ kind: 'value', path: ['settings'], key: 'mode', from: 18 })
    expect(at('settings:\n  "mode": |')).toMatchObject({ kind: 'value', key: 'mode' })
  })

  it('knows a list item, indented under its key or level with it', () => {
    expect(at('settings:\n  eq:\n    - Boots\n    - Peg|')).toMatchObject({ kind: 'item', path: ['settings'], key: 'eq' })
    expect(at('settings:\n  eq:\n  - Peg|')).toMatchObject({ kind: 'item', path: ['settings'], key: 'eq' })
  })

  it('treats a mapping inside a list as under the list key', () => {
    expect(at('settings:\n  list:\n    - x: 1\n      |')).toMatchObject({ kind: 'key', path: ['settings', 'list'] })
    expect(at('top:\n  - name:\n      inner|')).toMatchObject({ kind: 'key', path: ['top', 'name'] })
  })

  it('offers nothing in comments, flow collections or an item with no key', () => {
    expect(at('# sett|')).toBeNull()
    expect(at('a: [b, c|')).toBeNull()
    expect(at('- a|')).toBeNull()
  })
})

describe('suggestionsFor', () => {
  it('offers the keys under a path, most used first, with a colon to type after', () => {
    expect(suggestionsFor({ kind: 'key', path: ['settings'], from: 0 }, HINTS)).toEqual([
      { label: 'goal', apply: 'goal: ', detail: 'in 7 presets', kind: 'key', count: 7 },
      { label: 'crystals', apply: 'crystals:', detail: 'in 6 presets', kind: 'key', count: 6 },
      { label: 'mode', apply: 'mode: ', detail: 'in 5 presets', kind: 'key', count: 5 },
      { label: 'eq', apply: 'eq: ', detail: 'in 2 presets', kind: 'key', count: 2 },
    ])
    expect(suggestionsFor({ kind: 'key', path: ['settings', 'crystals'], from: 0 }, HINTS)[0]?.detail).toBe('in 1 preset')
  })

  it('offers the values of a key, in the order they are most used', () => {
    expect(suggestionsFor({ kind: 'value', path: ['settings'], key: 'goal', from: 0 }, HINTS).map((s) => s.label)).toEqual(['ganon', 'dungeons'])
    expect(suggestionsFor({ kind: 'value', path: ['settings'], key: 'unknown', from: 0 }, HINTS)).toEqual([])
  })

  it('offers a list item as a value or the first key of a mapping', () => {
    expect(suggestionsFor({ kind: 'item', path: ['settings'], key: 'eq', from: 0 }, HINTS).map((s) => s.label)).toEqual(['PegasusBoots'])
    expect(suggestionsFor({ kind: 'item', path: ['settings'], key: 'list', from: 0 }, HINTS).map((s) => s.label)).toEqual(['x'])
  })
})
