import aiocache

from alttprbot.models import TournamentResults

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)


async def insert_tournament_race(srl_id: str, episode_id: str, event: str, permalink=None, week=None, spoiler=None,
                                 status=None):
    key = f'tournament_race_{srl_id}'
    await TournamentResults.create(
        srl_id=srl_id,
        episode_id=episode_id,
        permalink=permalink,
        spoiler=spoiler,
        event=event,
        week=week,
        status=status
    )
    await CACHE.delete(key)


async def update_tournament_results_rolled(srl_id: str, permalink: str, week=None, status=None):
    key = f'tournament_race_{srl_id}'
    await TournamentResults.filter(
        srl_id=srl_id,
        status__isnull=True
    ).update(
        status=status,
        permalink=permalink,
        week=week
    )
    await CACHE.delete(key)


async def record_tournament_results(srl_id: str, results_json: str):
    key = f'tournament_race_{srl_id}'
    await TournamentResults.filter(
        srl_id=srl_id,
        status__isnull=True
    ).update(
        status='RECORDED',
        results_json=results_json
    )
    await CACHE.delete(key)


async def update_tournament_results(srl_id: str, status="STARTED"):
    key = f'tournament_race_{srl_id}'
    await TournamentResults.filter(
        srl_id=srl_id,
        status__isnull=True
    ).update(
        status=status
    )
    await CACHE.delete(key)


async def get_active_tournament_race(srl_id: str):
    key = f'tournament_race_{srl_id}'
    if await CACHE.exists(key):
        results = await CACHE.get(key)
    else:
        results = await TournamentResults.filter(
            srl_id=srl_id,
            status__isnull=True
        ).values(
            'id',
            'srl_id',
            'episode_id',
            'permalink',
            'bingosync_room',
            'bingosync_password',
            'spoiler',
            'event',
            'status',
            'results_json',
            'week',
            'written_to_gsheet'
        )
        await CACHE.set(key, results)
    return results[0] if results else None


async def get_active_tournament_race_by_episodeid(episode_id: str):
    results = await TournamentResults.filter(
        episode_id=episode_id
    ).values(
        'id',
        'srl_id',
        'episode_id',
        'permalink',
        'bingosync_room',
        'bingosync_password',
        'spoiler',
        'event',
        'status',
        'results_json',
        'week',
        'written_to_gsheet'
    )
    return results[0] if results else None


async def delete_active_tournament_race(srl_id: str):
    key = f'tournament_race_{srl_id}'
    await TournamentResults.filter(srl_id=srl_id, status__isnull=True).delete()
    await CACHE.delete(key)


async def delete_active_tournament_race_all(srl_id: str):
    key = f'tournament_race_{srl_id}'
    await TournamentResults.filter(srl_id=srl_id).delete()
    await CACHE.delete(key)


async def update_tournament_race_status(srl_id: int, status="STARTED"):
    await TournamentResults.filter(srl_id=srl_id).update(status=status)
