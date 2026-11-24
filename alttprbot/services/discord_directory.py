"""Discord lookups that services need answered, without importing the Discord bot.

The Discord front end registers its implementation at startup
(``alttprbot_discord.gateways.register()``); tests and the dev server register
fakes. Every lookup works without privileged gateway intents.

Elections use it to decide who may run an election (server Administrators and the
bot owner), who may vote (server members, holding a role if one is set), which
channels and roles the create form offers, and to post an election's message.
"""

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol


@dataclass(frozen=True)
class Named:
    id: int
    name: str


class Directory(Protocol):
    async def is_owner(self, user_id: int) -> bool:
        """Whether ``user_id`` owns the bot."""

    async def bot_guilds(self, guild_ids: Iterable[int]) -> list[Named]:
        """Those of ``guild_ids`` that the bot is in, sorted by name."""

    async def member_role_ids(self, guild_id: int, user_id: int) -> Optional[list[int]]:
        """The member's role ids, or None when they aren't in the server."""

    async def is_admin(self, guild_id: int, user_id: int) -> bool:
        """Whether ``user_id`` has Administrator in ``guild_id``."""

    async def admin_guilds(self, user_id: int) -> list[Named]:
        """Every server the bot is in where ``user_id`` has Administrator, sorted by name.
        One member lookup per server, so slow; the web app asks Discord with the
        person's own sign-in instead, and only API tokens need this."""

    async def guild_name(self, guild_id: int) -> Optional[str]:
        """The server's name, or None if the bot isn't in it."""

    async def text_channels(self, guild_id: int) -> list[Named]:
        """Text channels in the server that the bot can post in."""

    async def roles(self, guild_id: int) -> list[Named]:
        """The server's roles, except @everyone and bot-managed ones."""

    async def post_election(self, election_id: int) -> int:
        """Post the election's message in its channel and return the message id.
        Raises ``InvalidInputError`` with a readable reason when it can't."""


_directory: Optional[Directory] = None


def register(directory: Directory) -> None:
    global _directory
    _directory = directory


def get() -> Directory:
    if _directory is None:
        raise RuntimeError("No Discord directory registered; call alttprbot_discord.gateways.register() at startup.")
    return _directory
