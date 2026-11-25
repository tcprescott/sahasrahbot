/**
 * Drives the preset YAML editor (CodeMirror) in tests. jsdom can't type into a
 * contenteditable the way a browser does, so text goes in as an editor change,
 * which is what typing turns into.
 */
import { EditorView } from '@codemirror/view'
import { act, screen, waitFor } from '@testing-library/react'

export interface YamlEditorHandle {
  view: EditorView
  text: () => string
  /** Types at the cursor. */
  type: (text: string) => void
  /** Replaces everything. */
  replace: (text: string) => void
  /** Puts the cursor at `pos` (default: the end). */
  moveTo: (pos?: number) => void
}

/** The YAML editor named `name`, once its code has loaded. */
export async function findYamlEditor(name = 'Preset YAML'): Promise<YamlEditorHandle> {
  const view = await waitFor(() => {
    const found = EditorView.findFromDOM(screen.getByRole('textbox', { name }))
    if (!found) throw new Error('The YAML editor has not loaded yet')
    return found
  })
  const run = (fn: () => void) => act(fn)
  return {
    view,
    text: () => view.state.doc.toString(),
    type: (text) =>
      run(() => {
        const { from, to } = view.state.selection.main
        view.dispatch({ changes: { from, to, insert: text }, selection: { anchor: from + text.length }, userEvent: 'input.type' })
      }),
    replace: (text) => run(() => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: text }, userEvent: 'input' })),
    moveTo: (pos) => run(() => view.dispatch({ selection: { anchor: pos ?? view.state.doc.length } })),
  }
}
