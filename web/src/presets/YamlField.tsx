import { lazy, Suspense, useId, useRef } from 'react'
import { Button } from '../components'

// CodeMirror and the YAML parser are a few hundred KB, so only the pages that show
// a preset's YAML load them. Until they arrive, a plain text box (or <pre>) stands in.
const YamlEditor = lazy(() => import('./yaml/YamlEditor'))
const YamlView = lazy(() => import('./yaml/YamlView'))

export interface YamlFieldProps {
  value: string
  onChange: (value: string) => void
  /** Told the first problem with the YAML ("Line 3: ..."), or null when it parses. */
  onProblem?: (problem: string | null) => void
  /** Which randomizer's settings to suggest. */
  randomizer?: string
}

/** The preset's YAML: typed or pasted into a code editor, or loaded from a file on this device. */
export function YamlField(props: Readonly<YamlFieldProps>) {
  const labelId = useId()
  return (
    <Suspense fallback={<PlainYamlField {...props} labelId={labelId} />}>
      <YamlEditor {...props} labelId={labelId} />
    </Suspense>
  )
}

/** A preset's YAML, read-only, coloured once the editor code has loaded. */
export function YamlCode({ value }: Readonly<{ value: string }>) {
  return (
    <Suspense
      fallback={
        <pre className="yaml">
          <code>{value}</code>
        </pre>
      }
    >
      <YamlView value={value} label="Preset YAML" />
    </Suspense>
  )
}

function PlainYamlField({ value, onChange, labelId }: Readonly<YamlFieldProps & { labelId: string }>) {
  return (
    <div className="yaml-box">
      <div className="yaml-box__bar">
        <span className="field__label grow" id={labelId}>
          Preset YAML
        </span>
        <LoadYamlButton onLoad={onChange} />
      </div>
      <textarea
        aria-labelledby={labelId}
        className="yaml-editor"
        spellCheck={false}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

/** "Load a file": reads a .yaml file from this device into the editor. */
export function LoadYamlButton({ onLoad }: Readonly<{ onLoad: (text: string) => void }>) {
  const file = useRef<HTMLInputElement>(null)
  return (
    <>
      <Button variant="ghost" size="sm" icon="upload" className="yaml-box__tool" aria-label="Load a file" onClick={() => file.current?.click()}>
        Load<span className="yaml-box__load-more"> a file</span>
      </Button>
      <input
        ref={file}
        type="file"
        accept=".yaml,.yml,text/yaml"
        hidden
        onChange={async (e) => {
          const chosen = e.target.files?.[0]
          if (chosen) onLoad(await chosen.text())
          e.target.value = ''
        }}
      />
    </>
  )
}
