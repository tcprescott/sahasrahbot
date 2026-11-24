import './triforce.css'

/** Three lines as the game shows them: white text on black, centred. */
export function TriforcePreview({ lines, label }: Readonly<{ lines: string[]; label?: string }>) {
  return (
    <div className="triforce-preview" role="img" aria-label={label ?? `Triforce text: ${lines.filter(Boolean).join(' / ') || 'blank'}`}>
      {[0, 1, 2].map((i) => (
        <div key={i} className="triforce-preview__line">
          {lines[i] || ' '}
        </div>
      ))}
    </div>
  )
}
