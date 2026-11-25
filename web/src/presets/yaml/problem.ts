/**
 * Checks preset YAML as the person types, so the editor can mark the line and Save
 * can wait until it parses. The server checks again with PyYAML when it saves
 * (alttprbot/services/presets.py), so this only has to agree on what's broken.
 */
import { parseDocument } from 'yaml'

export interface YamlProblem {
  /** 1-based, as people count lines. */
  line: number
  column: number
  /** Offsets into the text, for the editor's underline. */
  from: number
  to: number
  message: string
}

// The yaml library's wording for the mistakes people make most, said plainly.
const PLAIN: Record<string, string> = {
  MULTILINE_IMPLICIT_KEY: 'a key here is missing its colon, or the line is indented wrongly',
  TAB_AS_INDENT: 'indent with spaces, not tabs',
  BLOCK_AS_IMPLICIT_KEY: 'a value and a new key are on the same line; put the key on a line of its own',
  MULTIPLE_DOCS: 'a preset is one YAML document, but this has more than one (a second ---)',
}

/** The first thing wrong with the YAML, or null when it parses (or is empty). */
export function findYamlProblem(text: string): YamlProblem | null {
  if (!text.trim()) return null
  // PyYAML lets a later duplicate key win, so don't call that an error here.
  const error = parseDocument(text, { uniqueKeys: false, prettyErrors: true }).errors[0]
  if (!error) return null
  const [from, to] = error.pos
  const at = error.linePos?.[0] ?? { line: 1, col: 1 }
  const wording = PLAIN[error.code] ?? error.message.split(/ at line \d+, column \d+/)[0]!
  return { line: at.line, column: at.col, from, to: Math.max(from, to), message: lowerFirst(wording.trim().replace(/\.$/, '')) }
}

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1)
}
