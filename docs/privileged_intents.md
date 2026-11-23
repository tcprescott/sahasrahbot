---
published: false
---

# Discord privileged intents

SahasrahBot does not use any of Discord's privileged gateway intents (members,
presences, message_content). Both Discord clients connect with
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
| `/rtggadmin blast`, `/rtggadmin report` | Reply that they're unavailable. | Filter by role in Server Settings > Members and contact people by hand, or post the verification link in an announcement that pings the role. |
| `/racerverification reverify` | Replies that it's unavailable. The reverification loop has been removed (it was never started anyway). New verifications through the button still work. | None. The verification message still mentions a reverify period, but nothing enforces it. |
| `/async permissions` with a role | Replies that it's unavailable. Granting to individual users still works. | Grant to individual users. |
| Inquiry (mod mail) threads | The bot mentions the support role in the new private thread. Discord adds members of that role who can view the thread, **if the role has fewer than 100 members**. The mention only counts if the role is mentionable or the bot has "Mention @everyone, @here, and All Roles" in the channel. Otherwise the bot posts a note asking a moderator to join by hand. | Keep the mod-mail role under 100 members and give the bot Mention All Roles in the inquiry channel. |

The main bot's `$` prefix commands only work as `@SahasrahBot command`, because
Discord only sends message text when the bot is mentioned.

### Audit bot

The audit bot only starts when `AUDIT_BOT_ENABLED = True` is set in `config.py` (default
off). When it runs:

| Feature | Behaviour |
|---|---|
| Message logging | Rows keep author, channel and time. Discord sends no text or attachments. |
| Deleted message log | Posted with author, channel and time only. |
| Edited message log | Skipped. |
| Link, executable, phishing and ROM moderation | Skipped, because Discord strips content and attachments. |
| Join/leave log | Not delivered by Discord. |
| Ban log | Works. |
| `messagehistory` / `deletedhistory` | Invoke as `@AuditBot messagehistory @user`. |

Discord AutoMod (Server Settings > Safety Setup) can partly cover the moderation side.
