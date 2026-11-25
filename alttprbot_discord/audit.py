"""Tells the audit log (``alttprbot/services/audit.py``) who is acting in Discord.

Slash commands and context menus get it from ``SentryCommandTree`` (``telemetry.py``),
prefix commands from the bot's ``before_invoke`` hook (``bot.py``). Buttons and
selects run outside both, so a callback that changes data is decorated with
:func:`audited`.
"""

import functools
from typing import Optional

import discord

from alttprbot.services import audit


def interaction_source(interaction: discord.Interaction, detail: Optional[str]) -> audit.Source:
    user = interaction.user
    return audit.Source(via=audit.VIA_DISCORD, detail=detail, actor_discord_id=user.id if user else None,
                        actor_name=getattr(user, 'name', None))


def context_source(ctx) -> audit.Source:
    """A prefix command's ``commands.Context``."""
    author = ctx.author
    name = getattr(ctx.command, 'qualified_name', None)
    return audit.Source(via=audit.VIA_DISCORD, detail=f'${name}' if name else None,
                        actor_discord_id=author.id if author else None, actor_name=getattr(author, 'name', None))


def audited(detail: str):
    """Decorate a button or select callback ``(self, interaction, ...)``: changes it
    makes are recorded as the person who pressed it, through ``detail`` (e.g.
    "Join button")."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            with audit.acting(interaction_source(interaction, detail)):
                return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator


async def bind_prefix_command(ctx) -> None:
    """``before_invoke`` hook: runs in the command's own task, so the source holds for
    the command body."""
    audit.set_source(context_source(ctx))
