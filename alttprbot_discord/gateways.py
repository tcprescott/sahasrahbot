"""Discord implementations of the lookups that services in ``alttprbot/`` need.

Services don't import the bot. ``sahasrahbot.py`` calls ``register()`` at startup,
which hands each service the Discord-backed function it asks for.
"""

import logging
from typing import List, Optional

import discord

from alttprbot.services import asynctournament as asynctournament_service
from alttprbot.services import asynctournament_jobs
from alttprbot.util import discord_members, seed_presenter
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import seed_embeds


async def member_role_ids(guild_id: int, discord_user_id: int) -> Optional[List[int]]:
    """Role IDs of a guild member, or None if the guild or member can't be found."""
    guild = discordbot.get_guild(guild_id)
    if guild is None:
        return None
    member = await discord_members.get_member(guild, discord_user_id)
    if member is None:
        return None
    return [r.id for r in member.roles]


async def notify_async_race_timeout(action: asynctournament_service.TimeoutAction) -> bool:
    """Tell the runner about a timeout in their race thread. False if the thread can't be found."""
    race = action.race
    thread = discordbot.get_channel(race.thread_id)
    if thread is None:
        logging.warning("Cannot access thread for race %s.  This should not have happened.", race.id)
        return False

    mention = f"<@{race.user.discord_user_id}>"
    if action.kind == asynctournament_service.WARN:
        msg = f"{mention}, your race will be permanently forfeit on {discord.utils.format_dt(action.deadline, 'f')} ({discord.utils.format_dt(action.deadline, 'R')}) if you do not start it by then.  Please start your run as soon as possible.  Please ping the @Admins if you require more time."
    elif action.kind == asynctournament_service.FORFEIT_PENDING:
        msg = f"{mention}, the grace period for the start of this run has elapsed.  This run has been forfeit.  Please contact the @Admins if you believe this was in error."
    else:
        msg = f"{mention}, this race has exceeded 12 hours.  This run has been forfeit.  Please contact the @Admins if you believe this was in error."

    await thread.send(msg, allowed_mentions=discord.AllowedMentions(users=True))
    return True


def register() -> None:
    asynctournament_service.set_member_role_lookup(member_role_ids)
    asynctournament_jobs.set_timeout_notifier(notify_async_race_timeout)
    # The tournament engine posts seed embeds through this hook instead of importing Discord code.
    seed_presenter.register(seed_embeds.seed_embed, seed_embeds.seed_tournament_embed)
