import * as RadixDialog from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'
import { Button } from './Button'
import { Icon } from './Icon'
import { RowMenu, type MenuItem } from './Menu'

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: ReactNode
  /** `side`: a panel down the right edge on desktop (a bottom sheet on phone, like the rest). */
  size?: 'sm' | 'md' | 'lg' | 'side'
  children: ReactNode
  footer?: ReactNode
}

/**
 * Centred card on desktop, bottom sheet on phone. Close is a soft grey disc
 * on phone and a "Close" pill on desktop; CSS shows the right one.
 */
export function Dialog({ open, onOpenChange, title, description, size = 'md', children, footer }: Readonly<DialogProps>) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="dialog-scrim" />
        <RadixDialog.Content className={`dialog dialog--${size}`}>
          <header className="dialog__head">
            <RadixDialog.Title className="dialog__title">{title}</RadixDialog.Title>
            <RadixDialog.Close asChild>
              <button type="button" className="dialog__close-disc" aria-label="Close">
                <Icon name="close" size={20} />
              </button>
            </RadixDialog.Close>
            <RadixDialog.Close asChild>
              <button type="button" className="dialog__close-pill">
                Close
              </button>
            </RadixDialog.Close>
          </header>
          {description ? (
            <RadixDialog.Description className="dialog__desc">{description}</RadixDialog.Description>
          ) : (
            <RadixDialog.Description className="visually-hidden">{title}</RadixDialog.Description>
          )}
          <div className="dialog__body">{children}</div>
          {footer && <footer className="dialog__foot">{footer}</footer>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}

interface FormDialogProps extends Omit<DialogProps, 'footer'> {
  primaryLabel: string
  onPrimary: () => void
  busy?: boolean
  busyLabel?: string
  /** The primary can't be pressed yet (say why in the dialog). */
  primaryDisabled?: boolean
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
  primaryDisabled = false,
  cancelLabel = 'Cancel',
  extra,
  destructive,
  ...dialog
}: Readonly<FormDialogProps>) {
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
          <Button
            variant={destructive ? 'danger' : 'primary'}
            onClick={onPrimary}
            busy={busy}
            busyLabel={busyLabel}
            disabled={primaryDisabled}
          >
            {primaryLabel}
          </Button>
        </>
      }
    />
  )
}
