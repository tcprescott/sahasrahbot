/**
 * Autocomplete for preset YAML: which keys and values fit where the cursor is,
 * from the keys SahasrahBot's own presets use (GET /api/v1/presets/randomizers/
 * {randomizer}/hints). Works on the text line by line, so it still helps while
 * the YAML is half typed and doesn't parse.
 */

export interface Hint {
  /** The keys above this one: [] is the top level, ['settings'] is under settings:. */
  path: string[]
  key: string
  /** How many of the shipped presets use it. */
  count: number
  /** Its most common values, written as YAML. */
  values: string[]
}

export type Spot =
  /** Typing a key in the mapping under `path`. */
  | { kind: 'key'; path: string[]; from: number }
  /** Typing the value of `key` (or an item of its list) in the mapping under `path`. */
  | { kind: 'value'; path: string[]; key: string; from: number }
  /** Typing after "- ": a list item, which may be a value or the first key of a mapping. */
  | { kind: 'item'; path: string[]; key: string; from: number }

export interface Suggestion {
  label: string
  /** What to insert, when it isn't just the label. */
  apply?: string
  detail?: string
  kind: 'key' | 'value'
  count: number
}

const KEY_LINE = /^(['"]?)([^'"#:\s][^'"#:]*?)\1:\s*(#.*)?$/
const VALUE_AT_CURSOR = /^(\s*)(-\s+)?(['"]?)([^'"#:\s][^'"#:]*?)\3:\s+(\S*)$/
const KEY_AT_CURSOR = /^(\s*)(-\s+)?([\w.-]*)$/

/** Where the cursor at `pos` is, as far as suggestions go, or null for nowhere useful. */
export function spotAt(text: string, pos: number): Spot | null {
  const lineStart = text.lastIndexOf('\n', pos - 1) + 1
  const before = text.slice(lineStart, pos)
  const value = VALUE_AT_CURSOR.exec(before)
  if (value) {
    const keyColumn = value[1]!.length + (value[2]?.length ?? 0)
    return { kind: 'value', path: parentPath(text, lineStart, keyColumn, false), key: value[4]!, from: pos - value[5]!.length }
  }
  const key = KEY_AT_CURSOR.exec(before)
  if (!key) return null
  const from = pos - key[3]!.length
  if (key[2]) {
    const path = parentPath(text, lineStart, key[1]!.length, true)
    if (!path.length) return null
    return { kind: 'item', path: path.slice(0, -1), key: path.at(-1)!, from }
  }
  return { kind: 'key', path: parentPath(text, lineStart, key[1]!.length, false), from }
}

/**
 * The keys of the mappings that hold a line indented by `column`, outermost first.
 * A list item ("- ") may sit at the same indent as its key, so `item` lets a
 * "key:" line at that very indent count as its parent.
 */
function parentPath(text: string, lineStart: number, column: number, item: boolean): string[] {
  const path: string[] = []
  let limit = column
  let sameIndentParent = item
  const lines = lineStart === 0 ? [] : text.slice(0, lineStart - 1).split('\n')
  for (let i = lines.length - 1; i >= 0 && limit > 0; i--) {
    const line = lines[i]!
    const trimmed = line.trimStart()
    const indent = line.length - trimmed.length
    if (!holdsLine(trimmed, indent, limit, sameIndentParent)) continue
    sameIndentParent = false
    const key = parentKey(trimmed, indent, limit)
    if (key) path.unshift(key)
    limit = indent
  }
  return path
}

/** Whether a line above, indented by `indent`, can hold a line at `limit`: it's less indented (or a "key:" level with a list item). */
function holdsLine(trimmed: string, indent: number, limit: number, sameIndentParent: boolean): boolean {
  if (!trimmed || trimmed.startsWith('#') || indent > limit) return false
  return indent < limit || (sameIndentParent && KEY_LINE.test(trimmed))
}

/**
 * The key a holding line opens, if it opens one ("key:" with nothing after it).
 * A list item's own key sits after its dash; when that's at our indent it's a sibling
 * in the same mapping, not a parent.
 */
function parentKey(trimmed: string, indent: number, limit: number): string | undefined {
  const dash = /^-\s+/.exec(trimmed)
  if (!dash) return KEY_LINE.exec(trimmed)?.[2]
  return indent + dash[0].length < limit ? KEY_LINE.exec(trimmed.slice(dash[0].length))?.[2] : undefined
}

function same(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((part, i) => part === b[i])
}

function plural(count: number): string {
  return count === 1 ? 'in 1 preset' : `in ${count} presets`
}

/** What to offer at `spot`, most used first. */
export function suggestionsFor(spot: Spot, hints: readonly Hint[]): Suggestion[] {
  const keysUnder = (path: string[]): Suggestion[] =>
    hints
      .filter((h) => same(h.path, path))
      .map((h) => {
        const parent = hints.some((child) => same(child.path, [...path, h.key]))
        return { label: h.key, apply: parent ? `${h.key}:` : `${h.key}: `, detail: plural(h.count), kind: 'key' as const, count: h.count }
      })
  const valuesOf = (path: string[], key: string): Suggestion[] => {
    const hint = hints.find((h) => h.key === key && same(h.path, path))
    return (hint?.values ?? []).map((v, i) => ({ label: v, kind: 'value' as const, count: hint!.values.length - i }))
  }
  if (spot.kind === 'key') return keysUnder(spot.path).sort(byCount)
  if (spot.kind === 'value') return valuesOf(spot.path, spot.key)
  return [...valuesOf(spot.path, spot.key), ...keysUnder([...spot.path, spot.key]).sort(byCount)]
}

function byCount(a: Suggestion, b: Suggestion): number {
  return b.count - a.count
}
