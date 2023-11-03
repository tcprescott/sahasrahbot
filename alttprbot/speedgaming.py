from dataclasses import dataclass, field
from typing import List
from datetime import datetime, timedelta
import logging

import aiohttp
import aiofiles
from dataclasses_json import LetterCase, dataclass_json, config
from marshmallow import fields
import pytz

from alttprbot.exceptions import SahasrahBotException
import settings


class SGEpisodeNotFoundException(SahasrahBotException):
    pass


class SGEventNotFoundException(SahasrahBotException):
    pass


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SpeedGamingPlayer:
    id: int
    display_name: str
    public_stream: str
    streaming_from: str
    discord_id: str
    discord_tag: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SpeedGamingCrew:
    id: int
    display_name: str
    language: str
    discord_id: str
    ready: bool
    partner: str
    discord_tag: str
    public_stream: str
    approved: bool


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SpeedGamingMatch:
    id: int
    note: str
    players: List[SpeedGamingPlayer]
    title: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SpeedGamingEvent:
    id: int
    bot_channel: str
    game: str
    name: str
    active: bool
    srtv: bool
    short_name: str
    srl: str
    slug: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SpeedGamingChannel:
    id: int
    language: str
    initials: str
    name: str
    slug: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SpeedGamingEpisode:
    id: int

    match1: SpeedGamingMatch
    match2: SpeedGamingMatch
    title: str
    approved: bool
    trackers: List[SpeedGamingCrew]
    when: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format='iso')
        )
    )
    event: SpeedGamingEvent
    channels: List[SpeedGamingChannel]
    length: int
    helpers: List[SpeedGamingCrew]
    external_restream: bool
    broadcasters: List[SpeedGamingCrew]
    timezone: str
    commentators: List[SpeedGamingCrew]
    when_countdown: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format='iso')
        )
    )


async def get_upcoming_episodes_by_event(event, hours_past=4, hours_future=4):
    if settings.DEBUG and event == 'test':
        test_schedule = []
        for episode_id in [1]:
            episode = await get_episode(episode_id)
            test_schedule.append(episode)
        return test_schedule

    now = datetime.now(tz=pytz.timezone('US/Eastern'))
    sched_from = now - timedelta(hours=hours_past)
    sched_to = now + timedelta(hours=hours_future)
    params = {
        'event': event,
        'from': sched_from.isoformat(),
        'to': sched_to.isoformat()
    }
    async with aiohttp.request(
        method='get',
        url=f'{settings.SG_API_ENDPOINT}/schedule',
        params=params,
    ) as resp:
        schedule = await resp.json(content_type='text/html')
        episode_ids = [episode['id'] for episode in schedule]
        logging.info(f'Retrieved schedule for {event} ({resp.status} {resp.reason}).  Received {len(schedule)} matches.  From: {sched_from} To: {sched_to}.  Match IDs: {", ".join(map(str, episode_ids))}')

    if 'error' in schedule:
        raise SGEventNotFoundException(f"Unable to retrieve schedule for {event}. {schedule.get('error')}")

    return schedule


async def get_episode(episodeid: int, complete=False):
    # if we're developing locally, we want to have some artifical data to use that isn't from SpeedGaming
    if settings.DEBUG:
        if episodeid == 1:
            async with aiofiles.open('test_input/sg_1.json', 'r') as f:
                result = f.read()
        elif episodeid == 2 and not complete:
            async with aiofiles.open('test_input/sg_2.json', 'r') as f:
                result = f.read()
        elif episodeid == 3 and complete:
            async with aiofiles.open('test_input/sg_3.json', 'r') as f:
                result = f.read()
        elif episodeid == 0:
            result = {"error": "Failed to find episode with id 0."}
        else:
            async with aiohttp.request(
                method='get',
                url=f'{settings.SG_API_ENDPOINT}/episode',
                params={'id': episodeid},
            ) as resp:
                result = await resp.text()
    else:
        async with aiohttp.request(
            method='get',
            url=f'{settings.SG_API_ENDPOINT}/episode',
            params={'id': episodeid},
        ) as resp:
            result = await resp.text()

    try:
        episode = SpeedGamingEpisode.from_json(result)
    except KeyError as e:
        raise SGEpisodeNotFoundException(result) from e

    return episode
