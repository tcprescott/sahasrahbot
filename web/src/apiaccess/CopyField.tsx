import { useState } from 'react'
import { IconButton } from '../components'

/** A value to copy (an address, a token) in a monospace box with a copy button. */
export function CopyField({ value, label }: Readonly<{ value: string; label: string }>) {
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
    <div className="copy-field">
      <span className="code copy-field__value">{value}</span>
      <IconButton icon={copied ? 'check_circle' : 'content_copy'} label={copied ? 'Copied' : label} onClick={() => void copy()} />
    </div>
  )
}
