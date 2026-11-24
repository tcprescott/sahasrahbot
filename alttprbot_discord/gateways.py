"""Discord implementations of the lookups that services in ``alttprbot/`` need.

Services don't import the bot. ``sahasrahbot.py`` calls ``register()`` at startup,
which hands each service the Discord-backed function it asks for.
"""

from alttprbot.services import bots
from alttprbot.util import seed_presenter
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import seed_embeds


def register() -> None:
    # The tournament engine and the web app reach the Discord client through this.
    bots.set_discord_client(discordbot)
    # The tournament engine posts seed embeds through this hook instead of importing Discord code.
    seed_presenter.register(seed_embeds.seed_embed, seed_embeds.seed_tournament_embed)
