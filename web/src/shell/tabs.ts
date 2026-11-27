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
  { path: '/seeds', label: 'Seeds', icon: 'change_history', match: (p) => p.startsWith('/seeds') },
  { path: '/presets', label: 'Presets', icon: 'folder', match: (p) => p.startsWith('/presets') },
  {
    path: '/me',
    label: 'Me',
    icon: 'person',
    match: (p) => p.startsWith('/me') || p.startsWith('/purgeme') || p.startsWith('/triforcetexts'),
  },
]

/** Shown to server admins only, between Presets and Me. */
export const ELECTIONS_TAB: Tab = {
  path: '/elections',
  label: 'Elections',
  icon: 'how_to_vote',
  match: (p) => p.startsWith('/elections') && !p.endsWith('/results'),
}

/** Shown to server admins only, after Elections: the Servers area (web/src/servers/). */
export const SERVERS_TAB: Tab = {
  path: '/servers',
  label: 'Servers',
  icon: 'forum',
  match: (p) => p.startsWith('/servers'),
}

/** The tabs a visitor sees: Elections and Servers only for someone who administers a server. */
export function tabsFor(serverAdmin: boolean): Tab[] {
  if (!serverAdmin) return TABS
  const me = TABS.findIndex((tab) => tab.path === '/me')
  return [...TABS.slice(0, me), ELECTIONS_TAB, SERVERS_TAB, ...TABS.slice(me)]
}

export const DOCS_URL = 'https://sahasrahbot.synack.live/'

/** The top bar's title for a path. */
export function titleFor(pathname: string): string {
  if (pathname.startsWith('/ranked_choice')) return 'Vote'
  if (pathname.startsWith('/elections') && pathname.endsWith('/results')) return 'Results'
  if (pathname.startsWith('/elections')) return 'Elections'
  if (pathname.startsWith('/triforcetexts')) return 'Triforce texts'
  if (pathname.startsWith('/submit')) return 'Race settings'
  if (pathname.startsWith('/audit')) return 'Audit log'
  if (pathname.startsWith('/servers')) return 'Servers'
  return TABS.find((tab) => tab.match(pathname))?.label ?? 'SahasrahBot'
}
