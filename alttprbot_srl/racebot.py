import asyncio
import re
import logging

from alttprbot.database import srl_races
# from alttprbot.tournament import league
from alttprbot.util.srl import srl_race_id
from config import Config as c

starting = re.compile(
    "\\x034\\x02The race will begin in 10 seconds!\\x03\\x02")
go = re.compile("\\x034\\x02GO!\\x03\\x02")
newroom = re.compile(
    "Race initiated for (.*)\. Join\\x034 (#srl-[a-z0-9]{5}) \\x03to participate\.")
runnerdone = re.compile(
    "(.*) (has forfeited from the race\.|has finished in .* place with a time of [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.)")
racedone = re.compile(
    "^Status: Complete \| Game: .*$"
)
permalink = re.compile(
    ".*https://alttpr\.com/.?.?.?h/([A-Za-z0-9]{10}).*"
)

srl_game_whitelist = [
    'Super Metroid Hacks',
    'Super Metroid'
]


async def topic_change_handler(target, source, message, client):
    if not (source == 'RaceBot' or source == 'synack'):
        return

    # if target.startswith('#srl-') and racedone.search(message):
    #     await asyncio.sleep(5)
    #     await league.process_league_race_finish(target, client)


async def handler(target, source, message, client):
    if not (source == 'RaceBot' or source == 'synack'):
        return
    srl_id = srl_race_id(target)

    if target == '#speedrunslive':
        asyncio.create_task(join_srl_room(client, message))

    if target.startswith('#srl-'):
        if starting.match(message) or message == 'test starting':
            asyncio.create_task(set_goal(srl_id, client, target))

        if message == 'test complete':
            await topic_change_handler(target, source, message, client)


async def join_srl_room(client, message):
    result = newroom.search(message)
    if result and result.group(1) in srl_game_whitelist:
        if not c.DEBUG:
            await asyncio.sleep(1)
            await client.join(result.group(2))
            await asyncio.sleep(60)
            await client.message(result.group(2), "Hi!  I'm SahasrahBot, your friendly robotic elder and randomizer seed roller.  To see what I can do, visit https://sahasrahbot.synack.live/srl.html")
        else:
            logging.info(f'would have joined {result.group(2)}')


async def set_goal(srl_id, client, target):
    race = await srl_races.get_srl_race_by_id(srl_id)
    if race:
        if not client.in_channel(target):
            await client.join(target)
        await client.message(target, f".setgoal {race['goal']}")
        if race['message'] is not None:
            await asyncio.sleep(15)
            await client.message(target, race['message'])
        await srl_races.delete_srl_race(srl_id)
