import { autocompletion, completionKeymap, type CompletionContext, type CompletionResult } from '@codemirror/autocomplete'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { bracketMatching, foldAll, indentOnInput, indentUnit, unfoldAll } from '@codemirror/language'
import { linter, lintGutter, type Diagnostic } from '@codemirror/lint'
import { Compartment, EditorState } from '@codemirror/state'
import { drawSelection, EditorView, highlightActiveLine, highlightActiveLineGutter, keymap } from '@codemirror/view'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Icon, type IconName } from '../../components'
import { LoadYamlButton, type YamlFieldProps } from '../YamlField'
import { loadHints } from './hintsCache'
import { spotAt, suggestionsFor, type Hint } from './hints'
import { findYamlProblem } from './problem'
import { yamlBasics } from './setup'

/**
 * The preset YAML editor: CodeMirror with the app's colours, a toolbar (load a file,
 * wrap lines, fold, full screen), a red underline and a status line for the first
 * thing that doesn't parse, and suggestions from SahasrahBot's own presets.
 * YamlField loads it lazily, so the rest of the app doesn't carry CodeMirror.
 */
export default function YamlEditor({ value, onChange, onProblem, randomizer, labelId }: Readonly<YamlFieldProps & { labelId: string }>) {
  const host = useRef<HTMLDivElement>(null)
  const view = useRef<EditorView | null>(null)
  const hints = useRef<readonly Hint[]>([])
  const wrapping = useRef(new Compartment())
  const latest = useRef({ onChange })
  latest.current = { onChange }
  const [wrap, setWrap] = useState(false)
  const [folded, setFolded] = useState(false)
  const [full, setFull] = useState(false)
  const [cursor, setCursor] = useState({ line: 1, column: 1 })
  const problem = useMemo(() => findYamlProblem(value), [value])

  useEffect(() => onProblem?.(problem ? `Line ${problem.line}: ${problem.message}.` : null), [problem, onProblem])

  useEffect(() => {
    let live = true
    hints.current = []
    if (randomizer) void loadHints(randomizer).then((loaded) => live && (hints.current = loaded))
    return () => {
      live = false
    }
  }, [randomizer])

  useEffect(() => {
    const complete = (context: CompletionContext): CompletionResult | null => {
      const spot = spotAt(context.state.doc.toString(), context.pos)
      if (!spot || (spot.from === context.pos && !context.explicit)) return null
      const options = suggestionsFor(spot, hints.current)
      if (!options.length) return null
      return {
        from: spot.from,
        options: options.map((s, i) => ({
          label: s.label,
          apply: s.apply,
          detail: s.detail,
          type: s.kind === 'key' ? 'property' : 'constant',
          boost: -i / options.length,
        })),
        validFor: /^[\w.'"-]*$/,
      }
    }
    const lint = (v: EditorView): Diagnostic[] => {
      const found = findYamlProblem(v.state.doc.toString())
      if (!found) return []
      const line = v.state.doc.lineAt(Math.min(found.from, v.state.doc.length))
      const from = Math.max(line.from, Math.min(found.from, line.to))
      const start = from === line.to && line.text.trim() ? line.from + (line.text.length - line.text.trimStart().length) : from
      const to = Math.max(start + 1, Math.min(found.to, line.to))
      return [{ from: start, to: Math.min(to, v.state.doc.length), severity: 'error', message: `Line ${found.line}: ${found.message}.` }]
    }
    const created = new EditorView({
      parent: host.current!,
      state: EditorState.create({
        doc: value,
        extensions: [
          ...yamlBasics({ 'aria-labelledby': labelId }),
          lintGutter(),
          linter(lint, { delay: 300 }),
          highlightActiveLine(),
          highlightActiveLineGutter(),
          drawSelection(),
          history(),
          indentOnInput(),
          bracketMatching(),
          indentUnit.of('  '),
          autocompletion({ override: [complete], icons: false }),
          keymap.of([...completionKeymap, ...defaultKeymap, ...historyKeymap, indentWithTab]),
          wrapping.current.of([]),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) latest.current.onChange(update.state.doc.toString())
            if (update.selectionSet || update.docChanged) {
              const head = update.state.selection.main.head
              const line = update.state.doc.lineAt(head)
              setCursor({ line: line.number, column: head - line.from + 1 })
            }
          }),
        ],
      }),
    })
    view.current = created
    return () => {
      created.destroy()
      view.current = null
    }
    // The editor is made once; later values arrive through the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // A value from outside (a loaded file) replaces what's in the editor.
  useEffect(() => {
    const current = view.current
    if (current && current.state.doc.toString() !== value) {
      current.dispatch({ changes: { from: 0, to: current.state.doc.length, insert: value } })
    }
  }, [value])

  useEffect(() => {
    view.current?.dispatch({ effects: wrapping.current.reconfigure(wrap ? EditorView.lineWrapping : []) })
  }, [wrap])

  useEffect(() => {
    if (!full) return
    const leave = (e: KeyboardEvent) => e.key === 'Escape' && !e.defaultPrevented && setFull(false)
    document.body.classList.add('yaml-full-open')
    window.addEventListener('keydown', leave)
    view.current?.focus()
    return () => {
      document.body.classList.remove('yaml-full-open')
      window.removeEventListener('keydown', leave)
    }
  }, [full])

  const goToProblem = () => {
    const current = view.current
    if (!current || !problem) return
    const at = Math.min(problem.from, current.state.doc.length)
    current.dispatch({ selection: { anchor: at }, effects: EditorView.scrollIntoView(at, { y: 'center' }) })
    current.focus()
  }

  return (
    <div className={full ? 'yaml-box yaml-box--full' : 'yaml-box'} role={full ? 'dialog' : undefined} aria-labelledby={full ? labelId : undefined}>
      <div className="yaml-box__bar">
        <span className="field__label grow" id={labelId}>
          Preset YAML
        </span>
        <LoadYamlButton onLoad={onChange} />
        <ToolButton icon="wrap_text" label="Wrap lines" pressed={wrap} onClick={() => setWrap(!wrap)} />
        <ToolButton
          icon={folded ? 'unfold_more' : 'unfold_less'}
          label={folded ? 'Unfold all' : 'Fold all'}
          onClick={() => {
            if (view.current) (folded ? unfoldAll : foldAll)(view.current)
            setFolded(!folded)
          }}
        />
        <ToolButton
          icon={full ? 'fullscreen_exit' : 'fullscreen'}
          label={full ? 'Exit full screen' : 'Full screen'}
          onClick={() => setFull(!full)}
        />
      </div>
      <div ref={host} className="yaml-box__editor" />
      <div className={problem ? 'yaml-box__status yaml-box__status--bad' : 'yaml-box__status'}>
        <span className="yaml-box__message" aria-live="polite">
          {problem ? (
            <>
              <Icon name="error" size={18} />
              <span>
                <b>Line {problem.line}:</b> {problem.message}.
              </span>
            </>
          ) : value.trim() ? (
            <>
              <Icon name="check_circle" size={18} />
              <span>Valid YAML</span>
            </>
          ) : (
            <span className="muted">Type or paste the preset, or load a file.</span>
          )}
        </span>
        {problem && (
          <button type="button" className="yaml-box__goto" onClick={goToProblem}>
            Go to line
          </button>
        )}
        <span className="yaml-box__pos">
          Ln {cursor.line}, Col {cursor.column}
        </span>
      </div>
    </div>
  )
}

function ToolButton({ icon, label, pressed, onClick }: Readonly<{ icon: IconName; label: string; pressed?: boolean; onClick: () => void }>) {
  return (
    <Button variant="ghost" size="sm" icon={icon} aria-label={label} aria-pressed={pressed} className="yaml-box__tool" onClick={onClick}>
      <span className="yaml-box__tool-label">{label}</span>
    </Button>
  )
}
