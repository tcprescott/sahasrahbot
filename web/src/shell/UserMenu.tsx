import type { IconName } from '../components/icons'
import { Button, Icon, Menu, type MenuItem } from '../components'
import { loginUrl } from '../api/client'
import { useSession } from '../auth/SessionProvider'
import { useTheme, type ThemeChoice } from '../theme/ThemeProvider'
import { useNavigate } from 'react-router-dom'
import { browser } from '../lib/browser'

const THEMES: { choice: ThemeChoice; label: string }[] = [
  { choice: 'system', label: 'Match my device' },
  { choice: 'light', label: 'Light' },
  { choice: 'dark', label: 'Dark' },
]

const THEME_ICONS: Record<ThemeChoice, IconName> = {
  system: 'brightness_auto',
  light: 'light_mode',
  dark: 'dark_mode',
}

function initials(name: string): string {
  return name.replace(/[^\p{L}\p{N}]/gu, '').slice(0, 2).toUpperCase() || '?'
}

/** The top bar's right side: Sign in, or the signed-in user's avatar menu. */
export function UserMenu() {
  const { user } = useSession()
  const { choice, setChoice } = useTheme()
  const navigate = useNavigate()

  const themeItems: MenuItem[] = THEMES.map((t) => ({
    label: `${t.choice === choice ? '✓ ' : ''}Theme: ${t.label}`,
    icon: THEME_ICONS[t.choice],
    onSelect: () => setChoice(t.choice),
  }))

  if (user === undefined) return null
  if (user === null) {
    return (
      <>
        <Menu
          trigger={
            <button type="button" className="icon-btn" aria-label="Theme">
              <Icon name="brightness_auto" />
            </button>
          }
          items={themeItems}
        />
        <Button asChild size="sm">
          <a href={loginUrl()}>
            <Icon name="login" size={18} />
            Sign in
          </a>
        </Button>
      </>
    )
  }
  return (
    <Menu
      header={`Signed in as ${user.name}`}
      trigger={
        <button type="button" className="user-pill" aria-label={`Account menu for ${user.name}`}>
          {user.avatar_url ? (
            <img className="avatar" src={user.avatar_url} alt="" />
          ) : (
            <span className="avatar" aria-hidden="true">
              {initials(user.name)}
            </span>
          )}
          <span className="user-pill__name">{user.name}</span>
          <Icon name="keyboard_arrow_down" size={18} />
        </button>
      }
      items={[
        { label: 'Me', icon: 'person', onSelect: () => navigate('/me') },
        ...themeItems,
        { label: 'Sign out', icon: 'logout', onSelect: () => browser.assign('/logout/') },
      ]}
    />
  )
}
