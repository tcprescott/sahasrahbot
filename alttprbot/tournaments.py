"""The tournament registry: which ``alttprbot/tournament/`` class runs each event.

``TOURNAMENT_DATA`` maps an event slug (the SpeedGaming event and racetime goal
the class handles) to its class. Opening rooms and recording results are in
``alttprbot/services/tournament_jobs.py`` and ``alttprbot/services/tournament_results.py``.
"""
import config
from alttprbot.tournament import test, dailies, alttprleague

if config.DEBUG:
    TOURNAMENT_DATA = {
        'test': test.TestTournament
    }
else:
    TOURNAMENT_DATA = {
        # Dailies/Weeklies
        'alttprdaily': dailies.AlttprSGDailyRace,
        'smz3': dailies.SMZ3DailyRace,

        # ALTTPR League
        'invleague': alttprleague.ALTTPRLeague,
        'alttprleague': alttprleague.ALTTPROpenLeague,
    }


async def fetch_tournament_handler(event, episodeid: int, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct(episodeid, rtgg_handler)


async def fetch_tournament_handler_v2(event, episode: dict, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct_with_episode_data(episode, rtgg_handler)
