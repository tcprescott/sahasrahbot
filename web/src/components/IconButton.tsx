import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Icon } from './Icon'
import type { IconName } from './icons'
import { Tooltip } from './Tooltip'

interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  icon: IconName
  /** Required: an icon-only control has no name without it. Also the tooltip. */
  label: string
  tooltip?: boolean
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon, label, tooltip = true, className, ...rest },
  ref,
) {
  const button = (
    <button ref={ref} type="button" aria-label={label} className={['icon-btn', className].filter(Boolean).join(' ')} {...rest}>
      <Icon name={icon} />
    </button>
  )
  return tooltip ? <Tooltip content={label}>{button}</Tooltip> : button
})
