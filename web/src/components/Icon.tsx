import { FILLED, ICONS, type IconName } from './icons'
import './Icon.css'

interface IconProps {
  name: IconName
  filled?: boolean
  size?: number
  className?: string
}

/** Decorative: the control around it carries the name. */
export function Icon({ name, filled = false, size = 22, className }: IconProps) {
  const Svg = (filled && FILLED[name]) || ICONS[name]
  return (
    <Svg
      className={['icon', className].filter(Boolean).join(' ')}
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
    />
  )
}
