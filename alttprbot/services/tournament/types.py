"""Presentation-neutral value objects exchanged by the tournament orchestrator.

The orchestrator (business tier) must not build ``discord.Embed`` objects, so a
``roll()`` returns a ``SeedResult`` carrying the generated seed plus any display
metadata. The Discord presenter turns it into embeds via
``presentation/discord/util/seed_embeds.py`` (``seed_embed`` / ``seed_tournament_embed``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


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
