/**
 * The sections of a server's page in the Servers area, in tab order. Each one is
 * also a child route of `servers/:guildId` in App.tsx (`<key>` or `<key>/*`), whose
 * component calls `useServer()` and renders only its own body: ServerScreen draws
 * the header and these tabs, and handles loading and errors.
 */
export interface ServerSection {
  key: string
  label: string
}

export const SECTIONS: ServerSection[] = [
  { key: 'settings', label: 'Settings' },
  { key: 'voice-roles', label: 'Voice roles' },
  { key: 'directory', label: 'Server directory' },
]

/** The section a server's page opens on. */
export const FIRST_SECTION = 'settings'

export const serverPath = (guildId: string, section: string = FIRST_SECTION) => `/servers/${guildId}/${section}`
