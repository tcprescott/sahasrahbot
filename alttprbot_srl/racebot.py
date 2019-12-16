import re
from config import Config as c
import asyncio
from alttprbot.util.srl import get_all_races, get_race, srl_race_id
from alttprbot.database import spoiler_races, srl_races
from alttprbot.util.http import request_generic, request_json_post
import ircmessage
import math

starting = re.compile("\\x034\\x02The race will begin in 10 seconds!\\x03\\x02")
go = re.compile("\\x034\\x02GO!\\x03\\x02")
newroom = re.compile("Race initiated for (.*)\. Join\\x034 (#srl-[a-z0-9]{5}) \\x03to participate\.")
runnerdone = re.compile("(.*) (has forfeited from the race\.|has finished in .* place with a time of [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.)")

srl_game_whitelist = [
    'The Legend of Zelda: A Link to the Past Hacks',
    'A Link to the Past & Super Metroid Combo Randomizer'
]

async def handler(target, source, message, client):
    if not (source == 'RaceBot' or source == 'synack'): return
    
    if target == '#speedrunslive':
        result = newroom.search(message)
        if result and result.group(1) in srl_game_whitelist:
            if not c.DEBUG:
                await asyncio.sleep(1)
                await client.join(result.group(2))
                await asyncio.sleep(60)
                await client.message(result.group(2), "Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR/SMZ3 seed roller.  To see what I can do, visit https://sahasrahbot.synack.live")
            else:
                print(f'would have joined {result.group(2)}')

    if target.startswith('#srl-'):
        if starting.match(message) or message=='test starting':
            srl_id = srl_race_id(target)
            race = await srl_races.get_srl_race_by_id(srl_id)
            if race:
                if not client.in_channel(target):
                    await client.join(target)
                await client.message(target, f".setgoal {race['goal']}")
                await srl_races.delete_srl_race(srl_id)

        if go.match(message) or message=='test go':
            srl_id = srl_race_id(target)

            await discord_race_start(srl_id)

            # spoilers
            race = await spoiler_races.get_spoiler_race_by_id(srl_id)
            if race:
                await client.message(target, 'Sending spoiler log...')
                await client.message(target, '---------------')
                await client.message(target, f"This race\'s spoiler log: {race['spoiler_url']}")
                await client.message(target, '---------------')
                await client.message(target, 'GLHF! :mudora:')
                await countdown_timer(
                    ircbot=client,
                    duration_in_seconds=race['studytime'],
                    srl_channel=target,
                    beginmessage=True,
                )
                await spoiler_races.delete_spoiler_race(srl_id)

        result = runnerdone.search(message)
        if result: await discord_race_finish(result)


async def discord_race_start(srl_id):
    if not c.DEBUG:
        await request_json_post(
            'http://localhost:5001/api/srl/start',
            data = {
                'auth': c.InternalApiToken,
                'raceid': srl_id
            },
            returntype='json'
        )

async def discord_race_finish(result):
    if not c.DEBUG:
        await request_json_post(
            'http://localhost:5001/api/srl/finish',
            data = {
                'auth': c.InternalApiToken,
                'nick': result.group(1)
            },
            returntype='json'
        )

async def countdown_timer(ircbot, duration_in_seconds, srl_channel, beginmessage=False):
    loop = asyncio.get_running_loop()

    reminders = [1800,1500,1200,900,600,300,120,60,30,10,9,8,7,6,5,4,3,2,1]
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
                msg = ircmessage.style(f"{seconds} second(s) remain!", fg='green', bold=True)
            else:
                msg = f'{minutes} minute(s), {seconds} seconds remain!'
            await ircbot.message(srl_channel, msg)
            reminders.remove(timeleft)
        if loop.time() >= end_time:
            if beginmessage:
                await ircbot.message(srl_channel, ircmessage.style('Log study has finished.  Begin racing!', fg='red', bold=True))
            break
        await asyncio.sleep(.5)