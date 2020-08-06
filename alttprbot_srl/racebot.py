import asyncio
import math
import re

import ircmessage

from alttprbot.database import spoiler_races, srl_races
from alttprbot.tournament import league
from alttprbot.util.srl import get_race, srl_race_id
from alttprbot_srl import alt_hunter, discord_integration, spoilers
from alttprbot_discord.util import alttpr_discord
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
    'The Legend of Zelda: A Link to the Past Hacks',
    'A Link to the Past & Super Metroid Combo Randomizer'
]


async def topic_change_handler(target, source, message, client):
    if not (source == 'RaceBot' or source == 'synack'):
        return

    if target.startswith('#srl-') and racedone.search(message):
        await asyncio.sleep(5)
        await league.process_league_race_finish(target, client)


async def handler(target, source, message, client):
    if not (source == 'RaceBot' or source == 'synack'):
        return
    srl_id = srl_race_id(target)

    if target == '#speedrunslive':
        asyncio.create_task(join_srl_room(client, message))

    if target.startswith('#srl-'):
        if starting.match(message) or message == 'test starting':
            asyncio.create_task(set_goal(srl_id, client, target))

        if go.match(message) or message == 'test go':
            asyncio.create_task(
                spoilers.send_spoiler_log(srl_id, client, target))
            asyncio.create_task(discord_integration.discord_race_start(srl_id))
            asyncio.create_task(alt_hunter.check_race(srl_id))

        if message == 'test complete':
            await topic_change_handler(target, source, message, client)

        result = runnerdone.search(message)
        if result:
            asyncio.create_task(
                discord_integration.discord_race_finish(result.group(1), srl_id))


async def join_srl_room(client, message):
    result = newroom.search(message)
    if result and result.group(1) in srl_game_whitelist:
        if not c.DEBUG:
            await asyncio.sleep(1)
            await client.join(result.group(2))
            await asyncio.sleep(60)
            await client.message(result.group(2), "Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR/SMZ3 seed roller.  To see what I can do, visit https://sahasrahbot.synack.live")
        else:
            print(f'would have joined {result.group(2)}')


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
    else:
        srl = await get_race(srl_id)
        if srl['game']['abbrev'] == 'alttphacks':
            result = permalink.match(srl['goal'])
            if result is not None:
                seed = await alttpr_discord.alttpr(hash_id=result.group(1))
                await client.message(target, f".setgoal vt8 randomizer - {seed.generated_goal}")


async def countdown_timer(ircbot, duration_in_seconds, srl_channel, beginmessage=False):
    loop = asyncio.get_running_loop()

    reminders = [1800, 1500, 1200, 900, 600, 300,
                 120, 60, 30, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    start_time = loop.time()
    end_time = loop.time() + duration_in_seconds
    while True:
        # print(datetime.datetime.now())
        timeleft = math.ceil(start_time - loop.time() + duration_in_seconds)
        # print(timeleft)
        if timeleft in reminders:
            minutes = math.floor(timeleft/60)
            seconds = math.ceil(timeleft % 60)
            if minutes == 0 and seconds > 10:
                msg = f'{seconds} second(s) remain!'
            elif minutes == 0 and seconds <= 10:
                msg = ircmessage.style(
                    f"{seconds} second(s) remain!", fg='green', bold=True)
            else:
                msg = f'{minutes} minute(s), {seconds} seconds remain!'
            await ircbot.message(srl_channel, msg)
            reminders.remove(timeleft)
        if loop.time() >= end_time:
            if beginmessage:
                await ircbot.message(srl_channel, ircmessage.style('Log study has finished.  Begin racing!', fg='red', bold=True))
            break
        await asyncio.sleep(.5)
