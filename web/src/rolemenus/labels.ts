import type { RoleMenuStyle } from '../api/client'

export const STYLES: { key: RoleMenuStyle; name: string; description: string; max: number }[] = [
  { key: 'buttons', name: 'Buttons', description: 'One button per role. People get a private “Added @role” reply. Up to 25 roles.', max: 25 },
  { key: 'dropdown', name: 'Dropdown', description: 'A dropdown with every role. Good for long lists. Up to 25 roles.', max: 25 },
  { key: 'reactions', name: 'Reactions', description: 'The classic: react with an emoji. No reply to the person. Up to 20 roles.', max: 20 },
]

export const styleName = (style: RoleMenuStyle) => STYLES.find((s) => s.key === style)?.name ?? style
export const styleMax = (style: RoleMenuStyle) => STYLES.find((s) => s.key === style)?.max ?? 25
