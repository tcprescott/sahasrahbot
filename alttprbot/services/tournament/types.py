"""Presentation-neutral value objects exchanged by the tournament orchestrator.

The orchestrator (business tier) must not build ``discord.Embed`` objects, so a
``roll()`` returns a ``SeedResult`` carrying the generated seed plus any display
metadata. The Discord presenter turns it into embeds via
``presentation/discord/util/seed_embeds.py`` (``seed_embed`` / ``seed_tournament_embed``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class SeedResult:
    """A generated tournament seed, decoupled from any presentation.

    ``seed`` is one of the ``services/seedgen/seedclasses`` ``*Seed`` objects (it
    carries ``url`` / ``code`` / ``hash`` and is what the presenter passes to
    ``seed_embed``). The remaining fields are optional display/business metadata the
    orchestrator may compute so the presenter and persistence layer never reach back
    into the seed internals.
    """

    seed: Any
    preset: Optional[str] = None
    goal: Optional[str] = None
    spoiler_url: Optional[str] = None
    permalink: Optional[str] = None

    @property
    def url(self) -> Optional[str]:
        if self.permalink is not None:
            return self.permalink
        return getattr(self.seed, "url", None)

    @property
    def code(self) -> Any:
        return getattr(self.seed, "code", None)


@dataclass
class TournamentPlayer:
    """A resolved tournament player, decoupled from ``discord.Member``.

    The presentation adapter resolves each SpeedGaming player to this neutral value
    object (RaceTime id + display name + discord user id) so the orchestrator can
    invite / DM / list players without holding a live Discord member object.
    """

    rtgg_id: Optional[str]
    name: Optional[str]
    discord_user_id: Optional[int]


@dataclass
class RaceRoom:
    """A presentation-neutral handle to an opened RaceTime room.

    ``start_race`` produces this; subsequent room operations key off ``name`` through
    the racetime gateway, so the orchestrator never holds the live race handler.
    """

    name: str
    url: str
    entrant_ids: List[str] = None

