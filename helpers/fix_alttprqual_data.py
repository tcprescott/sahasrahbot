import urllib.parse

import aiohttp
from tortoise import Tortoise
import isodate
import pytz

import config
from alttprbot import models

async def database():
    await Tortoise.init(
        db_url=f'mysql://{config.DB_USER}:{urllib.parse.quote_plus(config.DB_PASS)}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )

async def write_eligible_async_entrants(async_tournament_live_race: models.AsyncTournamentLiveRace,
                                        permalink: models.AsyncTournamentPermalink, race_room_data: dict):
    entrants = race_room_data.get('entrants', [])

    eligible_entrants_for_pool = []
    await async_tournament_live_race.fetch_related('tournament', 'pool')

    # iterate through entrants and create a AsyncTournamentRace record for each one
    for entrant in entrants:
        user, new = await models.Users.get_or_create(
            rtgg_id=entrant['user']['id'],
            defaults={
                'display_name': entrant['user']['name'],
                'twitch_name': entrant['user'].get('twitch_name', None),
            }
        )
        if not new:
            user.twitch_name = entrant['user'].get('twitch_name', None)
            await user.save()
        race_history = await models.AsyncTournamentRace.filter(
            tournament=async_tournament_live_race.tournament,
            user=user,
            permalink__pool=async_tournament_live_race.pool,
            reattempted=False
        )

        # skip if they've already raced in this pool the maximum number of times
        if len(race_history) >= async_tournament_live_race.tournament.runs_per_pool:
            continue

        # check if they have an active race already
        active_races = await models.AsyncTournamentRace.filter(
            tournament=async_tournament_live_race.tournament,
            user=user,
            status__in=['pending', 'in_progress'],
        )

        if active_races:
            continue

        await models.AsyncTournamentRace.create(
            tournament=async_tournament_live_race.tournament,
            permalink=permalink,
            user=user,
            thread_id=None,
            status='pending',
            live_race=async_tournament_live_race,
        )

        eligible_entrants_for_pool.append(user.display_name)

    return eligible_entrants_for_pool

async def process_async_tournament_start(async_tournament_live_race: models.AsyncTournamentLiveRace,
                                         race_room_data: dict):
    start_time = isodate.parse_datetime(race_room_data['started_at']).astimezone(pytz.utc)
    entrants = race_room_data.get('entrants', [])

    # update actual entrants to in_progress
    await models.AsyncTournamentRace.filter(
        live_race=async_tournament_live_race,
        status='pending',
        user__rtgg_id__in=[entrant['user']['id'] for entrant in entrants]
    ).update(
        status='in_progress',
        start_time=start_time
    )

    # delete any pending entrants that didn't actually join
    await models.AsyncTournamentRace.filter(
        live_race=async_tournament_live_race,
        status='pending'
    ).delete()

    async_tournament_live_race.status = 'in_progress'
    await async_tournament_live_race.save()

    in_progress_entrants = await models.AsyncTournamentRace.filter(
        live_race=async_tournament_live_race,
        status='in_progress'
    ).prefetch_related('user')

    return [entrant.user.display_name for entrant in in_progress_entrants]


async def get_racetime_room_data(racetime_slug):
    url = f'https://racetime.gg/{racetime_slug}/data'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

async def fix_tournament_data():
    live_async_race = await models.AsyncTournamentLiveRace.get(id=16)
    permalink = await models.AsyncTournamentPermalink.get(id=230)
    racetime_data = await get_racetime_room_data(live_async_race.racetime_slug)
    eligible_entrants = await write_eligible_async_entrants(live_async_race, permalink, racetime_data)
    print(f'Wrote {eligible_entrants} eligible entrants.')
    eligible_entrants = await process_async_tournament_start(live_async_race, racetime_data)
    print(f'Processed {eligible_entrants} entrants for tournament start.')

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(database())
    loop.run_until_complete(fix_tournament_data())