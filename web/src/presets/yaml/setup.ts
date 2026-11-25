/** CodeMirror pieces shared by the YAML editor and the read-only view: colours and gutters. */
import { yaml } from '@codemirror/lang-yaml'
import { foldGutter, HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { EditorState, type Extension } from '@codemirror/state'
import { EditorView, lineNumbers } from '@codemirror/view'
import { tags as t } from '@lezer/highlight'

// Syntax colours are the --code-* tokens in styles/tokens.css, so dark mode follows.
const highlight = HighlightStyle.define([
  { tag: [t.propertyName, t.definition(t.propertyName)], color: 'var(--code-key)' },
  { tag: [t.string, t.special(t.string)], color: 'var(--code-string)' },
  { tag: [t.number, t.bool, t.null, t.atom, t.keyword], color: 'var(--code-literal)' },
  { tag: t.comment, color: 'var(--code-comment)', fontStyle: 'italic' },
  { tag: [t.punctuation, t.separator, t.squareBracket, t.brace, t.meta], color: 'var(--fg-muted)' },
])

const theme = EditorView.theme({
  '&': { color: 'var(--fg)', backgroundColor: 'var(--surface)', fontSize: 'var(--text-sm)' },
  '.cm-scroller': { fontFamily: 'var(--font-mono)', lineHeight: '1.6', overflow: 'auto' },
  '.cm-content': { caretColor: 'var(--accent)', padding: '8px 0' },
  '.cm-gutters': { backgroundColor: 'var(--surface-alt)', color: 'var(--fg-muted)', borderRight: '1px solid var(--border-subtle)' },
  '.cm-activeLine': { backgroundColor: 'color-mix(in srgb, var(--accent) 6%, transparent)' },
  '.cm-activeLineGutter': { backgroundColor: 'color-mix(in srgb, var(--accent) 10%, transparent)', color: 'var(--fg)' },
  '&.cm-focused': { outline: 'none' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--accent)', borderLeftWidth: '2px' },
  '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground': {
    backgroundColor: 'color-mix(in srgb, var(--accent) 22%, transparent)',
  },
  '.cm-foldGutter span': { padding: '0 4px', cursor: 'pointer' },
  '.cm-foldPlaceholder': { backgroundColor: 'var(--surface-sunken)', border: '1px solid var(--border-subtle)', color: 'var(--fg-muted)' },
  '.cm-lintRange-error': { backgroundImage: 'none', textDecoration: 'underline wavy var(--status-cancelled)', textUnderlineOffset: '3px' },
  '.cm-lint-marker-error': { content: 'none' },
  '.cm-gutter-lint': { width: '6px' },
  '.cm-tooltip': {
    backgroundColor: 'var(--surface)',
    color: 'var(--fg)',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-2)',
    overflow: 'hidden',
  },
  '.cm-diagnostic-error': { borderLeftColor: 'var(--status-cancelled)' },
  '.cm-tooltip-autocomplete > ul': { fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', maxHeight: '220px' },
  '.cm-tooltip-autocomplete > ul > li': { padding: '4px 10px' },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: 'var(--accent-soft)', color: 'var(--fg)' },
  '.cm-completionDetail': { fontFamily: 'var(--font-body)', color: 'var(--fg-muted)', fontStyle: 'normal', marginLeft: '12px' },
  '.cm-completionMatchedText': { textDecoration: 'none', fontWeight: '700', color: 'var(--link)' },
})

/** YAML with the app's colours, line numbers and folding: what both the editor and the view use. */
export function yamlBasics(label: Record<string, string>): Extension[] {
  return [
    lineNumbers(),
    foldGutter({ openText: '▾', closedText: '▸' }),
    yaml(),
    syntaxHighlighting(highlight),
    theme,
    EditorState.tabSize.of(2),
    EditorView.contentAttributes.of(label),
  ]
}
