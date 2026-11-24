import * as DM from '@radix-ui/react-dropdown-menu'
import type { ReactNode } from 'react'
import { Button } from './Button'
import { Icon } from './Icon'
import { IconButton } from './IconButton'
import type { IconName } from './icons'

export interface MenuItem {
  label: string
  onSelect: () => void
  icon?: IconName
  /** Destructive items always sit last, under a divider, and should confirm before acting. */
  destructive?: boolean
  disabled?: boolean
}

function MenuContent({ items }: { items: MenuItem[] }) {
  const safe = items.filter((item) => !item.destructive)
  const destructive = items.filter((item) => item.destructive)
  const render = (item: MenuItem) => (
    <DM.Item
      key={item.label}
      className={['menu__item', item.destructive && 'menu__item--danger'].filter(Boolean).join(' ')}
      disabled={item.disabled}
      onSelect={item.onSelect}
    >
      {item.icon && <Icon name={item.icon} size={20} />}
      {item.label}
    </DM.Item>
  )
  return (
    <DM.Portal>
      <DM.Content className="menu" align="end" sideOffset={4} collisionPadding={8}>
        {safe.map(render)}
        {safe.length > 0 && destructive.length > 0 && <DM.Separator className="menu__sep" />}
        {destructive.map(render)}
      </DM.Content>
    </DM.Portal>
  )
}

/** The one ⋮ on a row or card. `label` names what it's for, e.g. "More for Thomas vs CheckRaise". */
export function RowMenu({ label, items }: { label: string; items: MenuItem[] }) {
  return (
    <DM.Root modal={false}>
      <DM.Trigger asChild>
        <IconButton icon="more_vert" label={label} tooltip={false} />
      </DM.Trigger>
      <MenuContent items={items} />
    </DM.Root>
  )
}

/** A page toolbar's secondary actions, beside its one main button. */
export function ActionsMenu({ items, label = 'Actions' }: { items: MenuItem[]; label?: string }) {
  return (
    <DM.Root modal={false}>
      <DM.Trigger asChild>
        <Button variant="outline">
          {label}
          <Icon name="keyboard_arrow_down" size={18} />
        </Button>
      </DM.Trigger>
      <MenuContent items={items} />
    </DM.Root>
  )
}

/** A menu on any trigger (the community picker, the avatar). */
export function Menu({ trigger, items, header }: { trigger: ReactNode; items: MenuItem[]; header?: ReactNode }) {
  return (
    <DM.Root modal={false}>
      <DM.Trigger asChild>{trigger}</DM.Trigger>
      <DM.Portal>
        <DM.Content className="menu" align="end" sideOffset={4} collisionPadding={8}>
          {header && <DM.Label className="menu__label">{header}</DM.Label>}
          {items.map((item) => (
            <DM.Item
              key={item.label}
              className={['menu__item', item.destructive && 'menu__item--danger'].filter(Boolean).join(' ')}
              disabled={item.disabled}
              onSelect={item.onSelect}
            >
              {item.icon && <Icon name={item.icon} size={20} />}
              {item.label}
            </DM.Item>
          ))}
        </DM.Content>
      </DM.Portal>
    </DM.Root>
  )
}
