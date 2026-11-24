import { NavLink, useLocation } from 'react-router-dom'
import { Icon } from '../components'
import { DOCS_URL, tabsFor } from './tabs'

/**
 * One list of destinations, drawn as a left rail on desktop and a bottom tab
 * bar on phone. Both are in the DOM; CSS shows one, and the hidden one is
 * display:none so it's out of the accessibility tree too.
 */
export function NavTabs({ variant, elections = false }: Readonly<{ variant: 'rail' | 'tabbar'; elections?: boolean }>) {
  const { pathname } = useLocation()
  const tabs = tabsFor(elections)
  return (
    <ul className={`nav nav--${variant}`}>
      {tabs.map((tab) => {
        const active = tab.match(pathname)
        return (
          <li key={tab.path}>
            <NavLink
              to={tab.path}
              end={tab.path === '/'}
              className={active ? 'nav__link active' : 'nav__link'}
              aria-current={active ? 'page' : undefined}
            >
              <span className="nav__icon">
                <Icon name={tab.icon} filled={active} />
              </span>
              <span className="nav__label">{tab.label}</span>
            </NavLink>
          </li>
        )
      })}
      {variant === 'rail' && (
        <li>
          <a className="nav__link" href={DOCS_URL} target="_blank" rel="noreferrer">
            <span className="nav__icon">
              <Icon name="menu_book" />
            </span>
            <span className="nav__label">Docs</span>
            <Icon name="open_in_new" size={16} className="nav__external" />
          </a>
        </li>
      )}
    </ul>
  )
}
