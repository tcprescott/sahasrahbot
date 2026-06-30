"""Live (resolved) tournament configuration for the Discord presentation layer.

``TournamentConfig`` is the Discord-resolved counterpart of the service-tier
``TournamentDefinition`` (which holds raw IDs): the orchestrator adapter resolves a
definition's guild/channel/role IDs into live ``discord`` objects and hands the cog
this value object. It lives in the presentation tier because it is built from, and
read as, live Discord objects.
"""

from dataclasses import dataclass

import discord


@dataclass
class TournamentConfig:
    guild: discord.Guild

    racetime_category: str
    racetime_goal: str
    event_slug: str

    schedule_type: str = "sg"

    audit_channel: discord.TextChannel = None
    commentary_channel: discord.TextChannel = None
    mod_channel: discord.TextChannel = None
    scheduling_needs_channel: discord.TextChannel = None
    create_scheduled_events: bool = False

    scheduling_needs_tracker: bool = False

    admin_roles: list = None
    helper_roles: list = None
    commentator_roles: list = None
    mod_roles: list = None

    stream_delay: int = 0
    room_open_time: int = 35
    auto_record: bool = False

    lang: str = 'en'
    coop: bool = False
