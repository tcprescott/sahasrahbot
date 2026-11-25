import { EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { useEffect, useRef } from 'react'
import { yamlBasics } from './setup'

/** A preset's YAML, coloured and foldable but not editable. Loaded only when shown (see YamlCode). */
export default function YamlView({ value, label }: Readonly<{ value: string; label: string }>) {
  const host = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const view = new EditorView({
      parent: host.current!,
      state: EditorState.create({
        doc: value,
        extensions: [...yamlBasics({ 'aria-label': label }), EditorState.readOnly.of(true), EditorView.editable.of(false)],
      }),
    })
    return () => view.destroy()
  }, [value, label])
  return <div ref={host} className="yaml-view" data-testid="yaml-view" />
}
