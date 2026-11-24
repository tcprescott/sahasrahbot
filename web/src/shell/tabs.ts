import type { IconName } from '../components'

export interface Tab {
  path: string
  label: string
  icon: IconName
  /** Other paths that light this tab up. */
  match: (pathname: string) => boolean
}

/** Shell A: the same tabs as a left rail on desktop and a bottom bar on phone. */
export const TABS: Tab[] = [
  { path: '/', label: 'Home', icon: 'home', match: (p) => p === '/' },
  { path: '/presets', label: 'Presets', icon: 'folder', match: (p) => p.startsWith('/presets') },
  {
    path: '/me',
    label: 'Me',
    icon: 'person',
    match: (p) => p.startsWith('/me') || p.startsWith('/purgeme') || p.startsWith('/triforcetexts'),
  },
]

export const DOCS_URL = 'https://sahasrahbot.synack.live/'

/** The top bar's title for a path. */
export function titleFor(pathname: string): string {
  if (pathname.startsWith('/ranked_choice')) return 'Vote'
  if (pathname.startsWith('/triforcetexts')) return 'Triforce texts'
  if (pathname.startsWith('/submit')) return 'Race settings'
  return TABS.find((tab) => tab.match(pathname))?.label ?? 'SahasrahBot'
}
