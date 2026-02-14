from datetime import datetime, timedelta

from alttprbot.models import SpoilerRaces


async def insert_spoiler_race(srl_id, spoiler_url, studytime=900):
    race = await SpoilerRaces.get_or_none(srl_id=srl_id)
    if race is None:
        await SpoilerRaces.create(srl_id=srl_id, spoiler_url=spoiler_url, studytime=studytime)
        return

    race.spoiler_url = spoiler_url
    race.studytime = studytime
    race.started = None
    await race.save()


async def start_spoiler_race(srl_id):
    await SpoilerRaces.filter(srl_id=srl_id).update(started=datetime.utcnow())


async def delete_spoiler_race(srl_id):
    await SpoilerRaces.filter(srl_id=srl_id).delete()


async def get_spoiler_races():
    results = await SpoilerRaces.all().values('id', 'srl_id', 'spoiler_url', 'studytime', 'date', 'started')
    return results


async def get_spoiler_race_by_id(srl_id):
    results = await SpoilerRaces.filter(
        srl_id=srl_id,
        started__isnull=True
    ).values('id', 'srl_id', 'spoiler_url', 'studytime', 'date', 'started')
    return results[0] if len(results) > 0 else False


async def get_spoiler_race_by_id_started(srl_id):
    results = await SpoilerRaces.filter(
        srl_id=srl_id,
        started__isnull=False
    ).values('id', 'srl_id', 'spoiler_url', 'studytime', 'date', 'started')

    if len(results) == 0:
        return False

    race = results[0]
    started = race['started']
    if started is None:
        return False

    now = datetime.now(tz=started.tzinfo) if started.tzinfo else datetime.utcnow()
    studytime = race['studytime'] or 0
    if now <= started + timedelta(seconds=studytime):
        return race

    return False
