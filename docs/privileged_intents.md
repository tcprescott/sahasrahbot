---
published: false
---

# Discord privileged intents

SahasrahBot does not use any of Discord's privileged gateway intents (members,
presences, message_content). The Discord client connects with
`discord.Intents.default()`. If a bot asks for a privileged intent it isn't approved
for, Discord closes the gateway connection (close code 4014) and the bot never comes
online, so don't add them back without approval for the application.

## Member lookups

`alttprbot/util/discord_members.py` gives you:

* `get_member(guild, user_id)`, which tries the cache and then falls back to `guild.fetch_member` (REST).
* `get_member_named(guild, name)`, which tries the cache and then falls back to `guild.query_members`.
  Discord's query only matches username and server-nickname prefixes, so a member known
  only by their global display name may not be found.

Without the members intent the cache is never complete, and `guild.chunk()`, `guild.members`
and `role.members` can't be used. There is no way to list the members of a guild or a
role.

## Features that can't work without intents

### Main bot

| Feature | Behaviour | Workaround |
|---|---|---|
| Bulk racetime.gg link reminders and racer reverification | Removed (`/rtggadmin blast`, `/rtggadmin report`, `/racerverification reverify`): they walked every member of a role. New verifications through the button still work. | Filter by role in Server Settings > Members and contact people by hand, or post the verification link in an announcement that pings the role. |
| Inquiry (mod mail) threads | The bot mentions the support role in the new private thread. Discord adds members of that role who can view the thread, **if the role has fewer than 100 members**. The mention only counts if the role is mentionable or the bot has "Mention @everyone, @here, and All Roles" in the channel. Otherwise the bot posts a note asking a moderator to join by hand. | Keep the mod-mail role under 100 members and give the bot Mention All Roles in the inquiry channel. |

The main bot's `$` prefix commands only work as `@SahasrahBot command`, because
Discord only sends message text when the bot is mentioned.

### Audit bot

The separate audit and moderation bot was removed: without the message_content and
members intents it could only log authors and bans. Discord AutoMod (Server Settings >
Safety Setup) and the server's own audit log cover most of it.
