export interface NavItem {
  label: string;
  to: string;
  /** external link (full URL) instead of a router route */
  external?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Home', to: '/' },
  { label: 'Presets', to: '/presets' },
  { label: 'Leaderboard', to: '/async/leaderboard/418' },
  { label: 'Submit', to: '/submit/alttprleague' },
  { label: 'GitHub', to: 'https://github.com/tcprescott/sahasrahbot', external: true },
];
