/** Role menu page URLs: the Role menus section of a server's page. `/rolemenus` in Discord links here. */
export const listPath = (guildId: string) => `/servers/${guildId}/role-menus`
export const newPath = (guildId: string) => `${listPath(guildId)}/new`
export const editPath = (guildId: string, id: number) => `${listPath(guildId)}/${id}`

/** A Discord link to the menu's message, or undefined when it isn't posted. */
export function messageUrl(menu: { guild_id: string; channel_id: string; message_id?: string | null }): string | undefined {
  return menu.message_id ? `https://discord.com/channels/${menu.guild_id}/${menu.channel_id}/${menu.message_id}` : undefined
}
