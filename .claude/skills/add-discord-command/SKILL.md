---
name: add-discord-command
description: >-
  Add or change a Discord command in SahasrahBot the way this codebase expects: a cog in
  alttprbot_discord/cogs/, registered in bot.py, a slash command that works without
  privileged intents, settings in config.example.py, and checks passing. Use whenever a
  task adds a Discord command, listener, or cog.
---

# Adding a Discord command

1. **Pick the cog.** Extend an existing cog in `alttprbot_discord/cogs/` when the command
   fits its topic. A new cog is a module with a `commands.Cog` subclass and an
   `async def setup(bot): await bot.add_cog(...)`, plus a
   `load_extension("alttprbot_discord.cogs.<name>")` line in `load_extensions()` in
   `alttprbot_discord/bot.py`. Gate debug-only cogs on `config.DEBUG`.
2. **Use a slash command** (`discord.app_commands`). Prefix commands depend on reading
   message text, which needs the message_content intent the bot doesn't have; they only
   work when the bot is mentioned.
3. **No member cache.** Without the members intent, `guild.members`, `role.members`,
   `guild.get_member` and `guild.chunk()` are empty or incomplete. Use
   `alttprbot/util/discord_members.py` (`get_member`, `get_member_named`), or take a
   `discord.Member` as a command parameter so Discord resolves it.
   `docs/privileged_intents.md` lists what can't be done at all.
4. **Logic out of the cog** where it's more than a few lines: seed rolling belongs in
   `alttprbot/alttprgen/`, data access in `alttprbot/models/`, shared helpers in
   `alttprbot/util/`. Embeds per randomizer live in `alttprbot_discord/util/`.
5. **Errors**: raise `SahasrahBotException` for messages the user should see; the error
   cog (`alttprbot_discord/cogs/errors.py`) shows them.
6. **Settings**: any new `config.NAME` goes in `config.example.py` with a placeholder.
   Tell the user what production needs.
7. **Docs**: if users will look the command up, update the public site in `docs/`
   (`docs/discord.md`).
8. **Check**: `./scripts/check.sh`. `tests/test_imports.py` imports every cog listed in
   `load_extensions()`, so a new cog is covered once it's registered there.
