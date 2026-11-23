---
published: false
---

# Running without Discord privileged intents

SahasrahBot's Discord application lost its approval for Discord's privileged
gateway intents. When a bot asks for a privileged intent it isn't approved for,
Discord closes the gateway connection (close code 4014, `PrivilegedIntentsRequired`
in discord.py) and the bot never comes online. Both Discord clients were affected:

| Client | Previously requested | Privileged intents in that set |
|---|---|---|
| Main bot (`alttprbot_discord/bot.py`) | `Intents.default()` + `members` | `members` |
| Audit bot (`alttprbot_audit/bot.py`) | `Intents.all()` | `members`, `presences`, `message_content` |

Both now run with `discord.Intents.default()` (no privileged intents) unless they are
turned back on in config. No feature code was removed; everything that depends on a
privileged intent is behind a check and comes back as soon as the flag is turned on.

## Turning the intents back on

Add these to `config.py` and restart once Discord has approved the intents again:

```python
DISCORD_PRIVILEGED_INTENTS = True        # main bot: members intent
AUDIT_DISCORD_PRIVILEGED_INTENTS = True  # audit bot: Intents.all(); defaults to DISCORD_PRIVILEGED_INTENTS
```

The audit bot is also switched off entirely for now. To start it again, add:

```python
AUDIT_BOT_ENABLED = True  # start the audit bot (sahasrahbot.py); defaults to False
```

It can run with or without `AUDIT_DISCORD_PRIVILEGED_INTENTS`. Without the intents it runs
in the reduced mode described under "Audit bot" below.

The intent flags default to `False`. The audit bot flag falls back to the main bot flag, so one line
is enough if both apps get approved at the same time. Make sure the intents are also
switched on for each application in the Discord Developer Portal (Bot > Privileged
Gateway Intents), or the bot will fail to connect again.

The logic is all in `alttprbot/util/discord_intents.py`:

* `main_bot_intents()` / `audit_bot_intents()` build the intents from the flags.
* `ensure_chunked(guild)` chunks the guild only when the members intent is on.
* `get_member(guild, id)` uses the cache, then falls back to `guild.fetch_member` (REST).
* `get_member_named(guild, name)` uses the cache, then falls back to `guild.query_members`.
* `get_role_members(role)` returns `None` when role membership can't be listed.

With the flags on, these behave exactly like the old `guild.chunk()` + `get_member()` code.

## What breaks while the intents are off

### Main bot (members intent)

| Feature | Where | What happens now | Workaround |
|---|---|---|---|
| `/blast` (DM every member of a role who hasn't linked RaceTime.gg) | `cogs/nickname.py` | Replies that it's unavailable. | Filter by role in Server Settings > Members and DM people by hand, or post the verification link (`/racetime/verification/initiate`) in an announcement that pings the role. |
| `/report` (list members of a role who haven't linked RaceTime.gg) | `cogs/nickname.py` | Replies that it's unavailable. | Same as above. A code workaround is possible: loop over `Users` rows with no `rtgg_id` and `fetch_member` each one to check the role, at the cost of one REST call per user. |
| Racer verification daily reverify loop and `/reverify` | `cogs/racer_verification.py` | Loop skips each verification with a log warning; `/reverify` replies that it's unavailable. No roles are revoked. New verifications through the button still work. | Wait for the intent. A code workaround is to reverify from the `VerifiedRacer` table plus `fetch_member` instead of the role's member list, but that would miss people who were given the role by hand. |
| `/async permissions` with a **role** | `cogs/asynctournament.py` | Replies that it's unavailable and asks for individual users. Granting to a **user** still works. | Insert an `AsyncTournamentPermissions` row with `discord_role_id` set (and `user` null). `alttprbot_api/util/checks.py` already honours role-ID rows, and it still works because it fetches the member's roles via REST. |
| Inquiry threads (mod mail) adding the support role's members | `cogs/inquiry.py` | The bot now mentions the role in the new private thread instead of adding each member. Discord adds the members of a mentioned role who can view the thread, **but only if the role has fewer than 100 members** (max 1,000 thread members). The mention only counts if it actually pings: the role must be mentionable, or the bot needs the "Mention @everyone, @here, and All Roles" permission in that channel. If neither is true, the bot posts a note in the thread saying the role must join manually. | Keep the support role under 100 members and give the bot Mention All Roles in the inquiry channel (or make the role mentionable). If the role is bigger, mods have to join by hand, or use a smaller dedicated "mod mail" role. |
| Member lookups by ID (tournament players, helper-role checks for RaceTime rooms, async tournament web permissions) | `alttprbot/tournament/core.py`, `alttprbot_api/util/checks.py`, `cogs/tournament.py` | Fall back to `fetch_member` over REST. Same result, one extra API call per lookup. | None needed. |
| Member lookups by Discord name (SpeedGaming players without a Discord ID, and the "bad player" report) | `alttprbot/tournament/core.py`, `cogs/tournament.py` | Fall back to a targeted `query_members`. Discord's search matches username and server nickname prefixes only, so a player listed on SpeedGaming by their global display name may not be found. | Make sure players have their Discord ID on their SpeedGaming profile, which is matched by ID first. |
| Guild chunking before `/cc2023`, the Challenge Cup delete-history button, and ranked-choice election creation | `cogs/tournament.py`, `cogs/rankedchoice.py` | Chunking is skipped. Nothing used the cache afterwards, so no change in behaviour. | None needed. |

Not affected: slash commands, seed generation, buttons/persistent views, reaction roles
(they already use `fetch_member`), voice roles (voice states are not privileged), the
RaceTime.gg bot, and the web API's OAuth and ranked-choice voting (both use REST).

Not new: the main bot never requested `message_content`, so its `$` prefix commands
(`$rr`, `$rg`, jishaku, and so on) have only worked as `@SahasrahBot command` since
discord.py 2.0. That hasn't changed.

### Audit bot (members, presences, message_content)

**The audit bot does not start at all** unless `AUDIT_BOT_ENABLED = True`, so every audit
feature (message logging, deleted/edited message logs, join/leave/ban logs, link/phishing/ROM
moderation, `$messagehistory`, `$deletedhistory`) is currently off. The table below describes
what you'd get if you turned it back on *before* its intents are restored.

| Feature | Where | What happens now | Workaround |
|---|---|---|---|
| Message content logging | `cogs/audit.py` `on_message` | Messages are still recorded with author, channel and time, but Discord sends no text or attachments, so content is blank. | None inside Discord. Discord's own audit log doesn't record message content. |
| Deleted message log | `cogs/audit.py` | Still posted with author, channel and timestamp. Content shows as "empty or unavailable". Messages recorded before the change still show their content until the 30-day cleanup removes them. | None. |
| Edited message log | `cogs/audit.py` `on_raw_message_edit` | Skipped, since there's no text to compare. | None. |
| Moderation: blocking `discord.gg` invites from members who joined in the last 24 hours, blocking executable uploads (`.bat/.exe/.sh/.py`), phishing-domain scan with a 30-minute timeout, deleting ROMs (`.sfc/.smc`, including inside `.zip`) | `cogs/moderation.py` | Disabled entirely, because Discord strips both content and attachments. | Discord AutoMod (Server Settings > Safety Setup > AutoMod): a custom keyword rule for `discord.gg/` and `discord.com/invite/` with an exemption for trusted roles, plus the built-in spam filters. AutoMod can't inspect attachment names, so blocking ROMs and executables has to be done by moderators. Server Settings > Safety Setup can also require a minimum account age or member age before posting. |
| Member join/leave log | `cogs/audit.py` `on_member_join`/`on_member_remove` | Discord no longer sends these events, so nothing is posted. | Turn on Discord's system "welcome" messages for joins. Kicks and bans show in the server's own audit log. Plain leaves have no built-in equivalent. |
| Ban log | `cogs/audit.py` `on_member_ban` | Still works (uses the non-privileged moderation intent). | None needed. |
| `$messagehistory` / `$deletedhistory` | `cogs/audit.py` | Use `@AuditBot messagehistory @user` instead of the `$` prefix, since Discord only sends message text when the bot is mentioned. The mention prefix is only added while the intents are off. New rows have blank content. | None. |
| Presences | none | Not used anywhere. | None needed. |
