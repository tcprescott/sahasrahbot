"""Submitted tournament game settings (``models.TournamentGames``), as other tools read
them over ``/api/tournament/games``."""

from typing import List, Mapping

from alttprbot import models


async def search(terms: Mapping[str, str]) -> List[dict]:
    """Every game matching ``terms``, as plain dicts of its columns.

    ``terms`` are Tortoise filter keyword arguments, passed through unchanged (the web
    route hands over its query string as is).
    """
    return await models.TournamentGames.filter(**terms).values()
