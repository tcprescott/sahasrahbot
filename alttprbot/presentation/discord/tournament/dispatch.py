"""Presentation-tier tournament dispatch.

The driving entry points the discord cog, the API blueprint, and the RaceTime handler use
to construct and drive a tournament event. Resolves the active ``TournamentEntry`` from the
service-tier registry and builds a ``TournamentCoordinator``. Replaces the dispatch
functions that lived in the untiered ``alttprbot/tournaments.py``.
"""

from alttprbot.presentation.discord.tournament.coordinator import TournamentCoordinator
from alttprbot.services import TournamentResultsService
from alttprbot.services.tournament import registry


async def fetch_tournament_handler(event, episodeid: int, rtgg_handler=None):
    return await TournamentCoordinator.construct(
        registry.TOURNAMENT_DATA[event], episodeid, rtgg_handler
    )


async def fetch_tournament_handler_v2(event, episode: dict, rtgg_handler=None):
    return await TournamentCoordinator.construct_with_episode_data(
        registry.TOURNAMENT_DATA[event], episode, rtgg_handler
    )


async def get_config(event):
    return await TournamentCoordinator.get_config(registry.TOURNAMENT_DATA[event])


async def create_tournament_race_room(event, episodeid):
    entry = registry.TOURNAMENT_DATA[event]
    proceed = await TournamentResultsService().handle_existing_room_for_episode(
        episodeid, entry.definition.racetime_category
    )
    if not proceed:
        return
    return await TournamentCoordinator.construct_race_room(entry, episodeid)
