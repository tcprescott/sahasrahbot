import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
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

function MenuContent({ items }: Readonly<{ items: MenuItem[] }>) {
  const safe = items.filter((item) => !item.destructive)
  const destructive = items.filter((item) => item.destructive)
  const render = (item: MenuItem) => (
    <DropdownMenu.Item
      key={item.label}
      className={['menu__item', item.destructive && 'menu__item--danger'].filter(Boolean).join(' ')}
      disabled={item.disabled}
      onSelect={item.onSelect}
    >
      {item.icon && <Icon name={item.icon} size={20} />}
      {item.label}
    </DropdownMenu.Item>
  )
  return (
    <DropdownMenu.Portal>
      <DropdownMenu.Content className="menu" align="end" sideOffset={4} collisionPadding={8}>
        {safe.map(render)}
        {safe.length > 0 && destructive.length > 0 && <DropdownMenu.Separator className="menu__sep" />}
        {destructive.map(render)}
      </DropdownMenu.Content>
    </DropdownMenu.Portal>
  )
}

/** The one ⋮ on a row or card. `label` names what it's for, e.g. "More for Thomas vs CheckRaise". */
export function RowMenu({ label, items }: Readonly<{ label: string; items: MenuItem[] }>) {
  return (
    <DropdownMenu.Root modal={false}>
      <DropdownMenu.Trigger asChild>
        <IconButton icon="more_vert" label={label} tooltip={false} />
      </DropdownMenu.Trigger>
      <MenuContent items={items} />
    </DropdownMenu.Root>
  )
}

/** A page toolbar's secondary actions, beside its one main button. */
export function ActionsMenu({ items, label = 'Actions' }: Readonly<{ items: MenuItem[]; label?: string }>) {
  return (
    <DropdownMenu.Root modal={false}>
      <DropdownMenu.Trigger asChild>
        <Button variant="outline">
          {label}
          <Icon name="keyboard_arrow_down" size={18} />
        </Button>
      </DropdownMenu.Trigger>
      <MenuContent items={items} />
    </DropdownMenu.Root>
  )
}

/** A menu on any trigger (the community picker, the avatar). */
export function Menu({ trigger, items, header }: Readonly<{ trigger: ReactNode; items: MenuItem[]; header?: ReactNode }>) {
  return (
    <DropdownMenu.Root modal={false}>
      <DropdownMenu.Trigger asChild>{trigger}</DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu" align="end" sideOffset={4} collisionPadding={8}>
          {header && <DropdownMenu.Label className="menu__label">{header}</DropdownMenu.Label>}
          {items.map((item) => (
            <DropdownMenu.Item
              key={item.label}
              className={['menu__item', item.destructive && 'menu__item--danger'].filter(Boolean).join(' ')}
              disabled={item.disabled}
              onSelect={item.onSelect}
            >
              {item.icon && <Icon name={item.icon} size={20} />}
              {item.label}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
