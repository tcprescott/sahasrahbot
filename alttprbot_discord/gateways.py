"""Discord implementations of the lookups that services in ``alttprbot/`` need.

Services don't import the bot. ``sahasrahbot.py`` calls ``register()`` at startup,
which hands each service the Discord-backed function it asks for.
"""

from alttprbot.observability import runtime
from alttprbot.services import bots
from alttprbot.util import seed_presenter
from alttprbot_discord.bot import discordbot
from alttprbot_discord import elections, server_directory, telemetry
from alttprbot_discord.util import seed_embeds


def register() -> None:
    # The tournament engine and the web app reach the Discord client through this.
    bots.set_discord_client(discordbot)
    # Elections: who administers which server, channels and roles, and posting.
    elections.register(discordbot)
    # The server directory: checking invites and posting the list.
    server_directory.register(discordbot)
    # The tournament engine posts seed embeds through this hook instead of importing Discord code.
    seed_presenter.register(seed_embeds.seed_embed, seed_embeds.seed_tournament_embed)
    # Discord latency and guild count for the Sentry metrics sampler.
    runtime.add_source('discord', telemetry.runtime_source(discordbot))
