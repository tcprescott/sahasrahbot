import { useRef } from 'react'
import { Button } from '../components'

/** The preset's YAML: typed or pasted in, or loaded from a file on this device. */
export function YamlField({ value, onChange, id = 'preset-yaml' }: { value: string; onChange: (value: string) => void; id?: string }) {
  const file = useRef<HTMLInputElement>(null)
  return (
    <div className="field">
      <div className="field__row">
        <label className="field__label" htmlFor={id}>
          Preset YAML
        </label>
        <Button variant="ghost" size="sm" icon="upload" onClick={() => file.current?.click()}>
          Load a file
        </Button>
        <input
          ref={file}
          type="file"
          accept=".yaml,.yml,text/yaml"
          hidden
          onChange={async (e) => {
            const chosen = e.target.files?.[0]
            if (chosen) onChange(await chosen.text())
            e.target.value = ''
          }}
        />
      </div>
      <textarea
        id={id}
        className="yaml-editor"
        spellCheck={false}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={'settings:\n  goal: ganon\n  ...'}
      />
    </div>
  )
}
