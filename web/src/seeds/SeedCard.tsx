import { useState } from 'react'
import { Button, Icon } from '../components'
import type { Seed } from './rolling'

/** Copies `value`, and says so on the button for two seconds. */
export function CopyButton({ value, label = 'Copy link' }: Readonly<{ value: string; label?: string }>) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }
  return (
    <Button variant="outline" icon={copied ? 'check_circle' : 'content_copy'} onClick={() => void copy()}>
      {copied ? 'Copied' : label}
    </Button>
  )
}

/** A seed just rolled: its link, file select code and anything the preset tells runners. */
export function SeedCard({ seed }: Readonly<{ seed: Seed }>) {
  return (
    <div className="seed-result">
      <a className="seed-result__link" href={seed.url} target="_blank" rel="noreferrer">
        {seed.url}
      </a>
      {seed.file_select_code && seed.file_select_code.length > 0 && (
        <ul className="seed-code" aria-label="File select code">
          {seed.file_select_code.map((item, i) => (
            <li key={`${i}-${item}`}>{item}</li>
          ))}
        </ul>
      )}
      <dl className="t-kv">
        <dt>Preset</dt>
        <dd>{seed.preset}</dd>
        {seed.hash && (
          <>
            <dt>Hash</dt>
            <dd>
              <span className="code">{seed.hash}</span>
            </dd>
          </>
        )}
        {seed.spoiler_url && (
          <>
            <dt>Spoiler log</dt>
            <dd>
              <a href={seed.spoiler_url} target="_blank" rel="noreferrer">
                Open the spoiler log
              </a>
            </dd>
          </>
        )}
      </dl>
      {seed.custom_instructions && <p className="seed-result__note">{seed.custom_instructions}</p>}
      <div className="t-actions">
        <Button asChild>
          <a href={seed.url} target="_blank" rel="noreferrer">
            <Icon name="open_in_new" size={18} />
            Open seed
          </a>
        </Button>
        <CopyButton value={seed.url} />
      </div>
    </div>
  )
}
