import { lazy, Suspense, useId, useRef, useState, type ReactNode } from 'react'
import { api, unwrap } from '../api/client'
import { Banner, Button } from '../components'

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
  /**
   * Told when a loaded file was an ALTTPR customizer save, converted to preset YAML.
   * A page that can change the randomizer sets it to alttpr here; without this, a
   * customizer save is only accepted when `randomizer` is already alttpr.
   */
  onCustomizerImported?: () => void
}

/** What the editor's file loader hands it: a file chosen on this device. */
export type LoadFile = (file: File) => Promise<void>

type Notice = { tone: 'info' | 'error'; text: ReactNode }

const CUSTOMIZER_KEY = /^(randomizer|vt\.custom)\./

/** A .json file, or text that's a JSON object with the customizer's keys. */
export function isCustomizerSave(fileName: string, text: string): boolean {
  if (fileName.toLowerCase().endsWith('.json')) return true
  if (!text.trimStart().startsWith('{')) return false
  try {
    const parsed: unknown = JSON.parse(text)
    return typeof parsed === 'object' && parsed !== null && Object.keys(parsed).some((key) => CUSTOMIZER_KEY.test(key))
  } catch {
    return false
  }
}

/** The preset's YAML: typed or pasted into a code editor, or loaded from a file on this device. */
export function YamlField(props: Readonly<YamlFieldProps>) {
  const labelId = useId()
  const [notice, setNotice] = useState<Notice | null>(null)
  const { onChange, onCustomizerImported, randomizer } = props

  const loadFile: LoadFile = async (file) => {
    const text = await file.text()
    if (!isCustomizerSave(file.name, text)) {
      setNotice(null)
      onChange(text)
      return
    }
    if (!onCustomizerImported && randomizer && randomizer !== 'alttpr') {
      setNotice({ tone: 'error', text: `${file.name} is an ALTTPR customizer save, and this preset is for ${randomizer}.` })
      return
    }
    try {
      const converted = unwrap(await api.POST('/api/v1/presets/customizer', { body: { content: text } }))
      onChange(converted.content)
      onCustomizerImported?.()
      setNotice({
        tone: 'info',
        text: (
          <>
            <b>Converted {file.name}</b> from an ALTTPR customizer save.
            {onCustomizerImported ? ' Randomizer is set to alttpr; check' : ' Check'} the YAML, then save.
          </>
        ),
      })
    } catch (err) {
      setNotice({ tone: 'error', text: (err as Error).message })
    }
  }

  return (
    <>
      {notice && <Banner tone={notice.tone}>{notice.text}</Banner>}
      <Suspense fallback={<PlainYamlField {...props} labelId={labelId} loadFile={loadFile} />}>
        <YamlEditor {...props} labelId={labelId} loadFile={loadFile} />
      </Suspense>
    </>
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

function PlainYamlField({ value, onChange, labelId, loadFile }: Readonly<YamlFieldProps & { labelId: string; loadFile: LoadFile }>) {
  return (
    <div className="yaml-box">
      <div className="yaml-box__bar">
        <span className="field__label grow" id={labelId}>
          Preset YAML
        </span>
        <LoadYamlButton onLoad={loadFile} />
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

/** "Load a file": a preset .yaml, or an ALTTPR customizer save (.json) to convert. */
export function LoadYamlButton({ onLoad }: Readonly<{ onLoad: LoadFile }>) {
  const file = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        icon="upload"
        className="yaml-box__tool"
        aria-label="Load a file"
        title="A preset .yaml file, or an ALTTPR customizer save (.json)"
        busy={busy}
        busyLabel="Converting"
        onClick={() => file.current?.click()}
      >
        Load<span className="yaml-box__load-more"> a file</span>
      </Button>
      <input
        ref={file}
        type="file"
        accept=".yaml,.yml,.json,text/yaml,application/json"
        hidden
        onChange={async (e) => {
          const chosen = e.target.files?.[0]
          e.target.value = ''
          if (!chosen) return
          setBusy(true)
          try {
            await onLoad(chosen)
          } finally {
            setBusy(false)
          }
        }}
      />
    </>
  )
}
