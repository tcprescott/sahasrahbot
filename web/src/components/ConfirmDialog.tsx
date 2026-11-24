import { useState, type ReactNode } from 'react'
import { FormDialog } from './Dialog'

/**
 * The confirmation every destructive menu item opens: says what will happen,
 * then does it. The dialog closes when `onConfirm` finishes, unless it
 * resolves `false` to stay open (it showed its own error).
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  children,
  action,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  children: ReactNode
  action: string
  onConfirm: () => Promise<boolean | void>
}) {
  const [busy, setBusy] = useState(false)
  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      size="sm"
      primaryLabel={action}
      destructive
      busy={busy}
      onPrimary={async () => {
        setBusy(true)
        const ok = await onConfirm()
        setBusy(false)
        if (ok !== false) onOpenChange(false)
      }}
    >
      <p className="confirm-dialog__text">{children}</p>
    </FormDialog>
  )
}
