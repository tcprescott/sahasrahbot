import * as RD from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'
import { Button } from './Button'
import { Icon } from './Icon'
import { RowMenu, type MenuItem } from './Menu'

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: ReactNode
  size?: 'sm' | 'md' | 'lg'
  children: ReactNode
  footer?: ReactNode
}

/**
 * Centred card on desktop, bottom sheet on phone. Close is a soft grey disc
 * on phone and a "Close" pill on desktop; CSS shows the right one.
 */
export function Dialog({ open, onOpenChange, title, description, size = 'md', children, footer }: DialogProps) {
  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="dialog-scrim" />
        <RD.Content className={`dialog dialog--${size}`}>
          <header className="dialog__head">
            <RD.Title className="dialog__title">{title}</RD.Title>
            <RD.Close asChild>
              <button type="button" className="dialog__close-disc" aria-label="Close">
                <Icon name="close" size={20} />
              </button>
            </RD.Close>
            <RD.Close asChild>
              <button type="button" className="dialog__close-pill">
                Close
              </button>
            </RD.Close>
          </header>
          {description ? (
            <RD.Description className="dialog__desc">{description}</RD.Description>
          ) : (
            <RD.Description className="visually-hidden">{title}</RD.Description>
          )}
          <div className="dialog__body">{children}</div>
          {footer && <footer className="dialog__foot">{footer}</footer>}
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  )
}

interface FormDialogProps extends Omit<DialogProps, 'footer'> {
  primaryLabel: string
  onPrimary: () => void
  busy?: boolean
  busyLabel?: string
  cancelLabel?: string
  /** Anything beyond Cancel and the primary goes in a ⋮ at the far left. */
  extra?: MenuItem[]
  destructive?: boolean
}

/** Footer on one line: extras ⋮ at far left, then Cancel, then the primary on the right. */
export function FormDialog({
  primaryLabel,
  onPrimary,
  busy,
  busyLabel,
  cancelLabel = 'Cancel',
  extra,
  destructive,
  ...dialog
}: FormDialogProps) {
  return (
    <Dialog
      {...dialog}
      footer={
        <>
          {extra && extra.length > 0 && <RowMenu label="More options" items={extra} />}
          <span className="dialog__spacer" />
          <Button variant="ghost" onClick={() => dialog.onOpenChange(false)}>
            {cancelLabel}
          </Button>
          <Button variant={destructive ? 'danger' : 'primary'} onClick={onPrimary} busy={busy} busyLabel={busyLabel}>
            {primaryLabel}
          </Button>
        </>
      }
    />
  )
}
