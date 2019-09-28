import argparse
import asyncio
import re
import shlex
import time
import json

import aioschedule as schedule
import pydle
import aiohttp

from alttprbot.alttprgen.preset import get_preset
from alttprbot.alttprgen.random import generate_random_game
from alttprbot.alttprgen.weights import weights
from alttprbot.database import srl_races
from alttprbot.database import spoiler_races
from alttprbot.util import orm
from config import Config as c

starting = re.compile("\\x034\\x02The race will begin in 10 seconds!\\x03\\x02")
go = re.compile("\\x034\\x02GO!\\x03\\x02")
newroom = re.compile("Race initiated for The Legend of Zelda: A Link to the Past Hacks\. Join\\x034 (#srl-[a-z0-9]{5}) \\x03to participate\.")


class SrlBot(pydle.Client):
    async def on_connect(self):
        await self.message('NickServ', 'identify ' + c.SRL_PASSWORD)
        await self.join('#speedrunslive')

    # target = channel of the message
    # source = sendering of the message
    # message = the message, duh
    async def on_message(self, target, source, message):
        # print messages to stdout for debugging purposes.  We should eventually set this up so it writes to a log file or something.
        print('MESSAGE: ' + target + ' - ' + source +
              ' - ' + message)  # dumb debugging message

        # filter messages sent by the bot (we do not want to react to these)
        if source == c.SRL_NICK:
            return

        # next lets react to any stuff we're interested in hearing from RaceBot
        if target == '#speedrunslive' and source == 'RaceBot':
            result = newroom.search(message)
            if result:
                if not c.DEBUG:
                    await asyncio.sleep(1)
                    await self.join(result.group(1))
                    await asyncio.sleep(60)
                    await self.message(result.group(1), "Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR seed roller.  To see what I can do, visit https://sahasrahbot.synack.live/srl.html")
                else:
                    print(f'would have joined {result.group(1)}')

        if target.startswith('#srl-') and source == 'RaceBot':
            if starting.match(message):
                srl_id = srl_race_id(target)
                race = await srl_races.get_srl_race_by_id(srl_id)
                if race:
                    if not client.in_channel(target):
                        await client.join(target)
                    await client.message(target, f".setgoal {race['goal']}")
                    await srl_races.delete_srl_race(srl_id)

            # if go.match(message):
            #     srl_id = srl_race_id(target)
            #     race = await srl_races.get_srl_race_by_id(srl_id)
            #     if race:
            #         # to be used in the future by spoiler races
            #         print("would have fired something on race start")
            #         pass


        # Handle any messages that start with $
        if message[0] == '$':
            split_msg = ['sb'] + shlex.split(message)

            parser = argparse.ArgumentParser()
            parser.add_argument('base', type=str)

            subparsers = parser.add_subparsers(dest="command")

            parser_preset = subparsers.add_parser('$preset')
            parser_preset.add_argument('preset')
            parser_preset.add_argument('--hints', action='store_true')

            parser_custom = subparsers.add_parser('$custom')

            parser_spoiler = subparsers.add_parser('$spoiler')
            parser_spoiler.add_argument('preset')
            parser_spoiler.add_argument('--studyperiod', type=int)

            parser_random = subparsers.add_parser('$random')
            parser_random.add_argument('weightset', nargs='?', default="weighted")

            parser_join = subparsers.add_parser('$joinroom')
            parser_join.add_argument('channel')

            parser_leave = subparsers.add_parser('$leave')

            parser_vt = subparsers.add_parser('$vt')

            parser_echo = subparsers.add_parser('$echo')
            parser_echo.add_argument('message')

            parser_help = subparsers.add_parser('$help')

            try:
                args = parser.parse_args(split_msg)
            except argparse.ArgumentError as e:
                await self.message(e)
            # print(args)

            if args.command == '$preset' and target.startswith('#srl-'):
                await self.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
                srl_id = srl_race_id(target)
                seed, preset_dict = await get_preset(args.preset, hints=args.hints, spoilers_ongen=False)
                goal_name = preset_dict['goal_name']
                if not seed:
                    await self.message(target, "That preset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live/srl.html")
                    return
                goal = f"vt8 randomizer - {goal_name}"
                code = await seed.code()
                await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
                await srl_races.insert_srl_race(srl_id, goal)

            if args.command == '$random' and target.startswith('#srl-'):
                await self.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
                srl_id = srl_race_id(target)
                seed = await generate_random_game(logic='NoGlitches', weightset=args.weightset, tournament=True)
                code = await seed.code()
                goal = f"vt8 randomizer - random {args.weightset}"
                await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
                await srl_races.insert_srl_race(srl_id, goal)

            if args.command == '$custom' and target.startswith('#srl-'):
                await self.message(target, "Not yet implemented.  Sorry!")

            if args.command == '$spoiler' and target.startswith('#srl-'):
                await self.message(target, "Not yet implemented.  Sorry!")

            if args.command == '$help' and target.startswith('#srl-'):
                await self.message(target, "For documentation on using this bot, visit https://sahasrahbot.synack.live/srl.html")

            if args.command == '$joinroom':
                await self.join(args.channel)

            if args.command == '$leave' and target.startswith('#srl-'):
                await self.part(target)

            if args.command == '$vt' and target.startswith('#srl-'):
                await self.message(target, "You summon VT, he looks around confused and curses your next game with bad RNG.")

            if args.command == '$echo':
                await self.message(source, args.message)

    # target = you
    # source = sendering of the message
    # message = the message, duh
    async def on_notice(self, target, source, message):
        print('NOTICE: ' + target + ' - ' + source +
              ' - ' + message)  # dumb debugging message

        # do stuff that we want after getting recognized by NickServ
        if message == 'Password accepted - you are now recognized.':
            await asyncio.sleep(1)
            await join_active_races('alttphacks')
            await process_active_races()
            # schedule.every(1).minutes.do(join_active_races, 'alttphacks')
            # schedule.every(1).minutes.do(process_active_races)
            # await self.join('#srl-pees0')


async def join_active_races(game):
    races = await get_all_races()
    for race in races['races']:
        if race['game']['abbrev'] == game:
            race_id=race['id']
            if not client.in_channel(f'#srl-{race_id}'):
                if c.DEBUG:
                    print(f'would have joined #srl-{race_id}')
                else:
                    await client.join(f'#srl-{race_id}')

async def process_active_races():
    print('process active races running')
    active_races = await srl_races.get_srl_races()
    for active_race in active_races:
        race = await get_race(active_race['srl_id'])
        channel_name = f"#srl-{active_race['srl_id']}"
        if not race:
            await srl_races.delete_srl_race(active_race['srl_id'])
        elif not race['state'] == 1:
            if not client.in_channel(channel_name):
                await client.join(channel_name)
            await client.message(channel_name, f".setgoal {active_race['goal']}")
            await srl_races.delete_srl_race(active_race['srl_id'])

async def get_race(raceid):
    return await request_generic(f'http://api.speedrunslive.com/races/{raceid}', returntype='json')

async def get_all_races():
    return await request_generic(f'http://api.speedrunslive.com/races', returntype='json')

def srl_race_id(channel):
    if re.search('^#srl-[a-z0-9]{5}$', channel):
        return channel.partition('-')[-1]

async def request_generic(url, method='get', reqparams=None, data=None, header={}, auth=None, returntype='text'):
    async with aiohttp.ClientSession(auth=None, raise_for_status=True) as session:
        async with session.request(method.upper(), url, params=reqparams, data=data, headers=header, auth=auth) as resp:
            if returntype == 'text':
                return await resp.text()
            elif returntype == 'json':
                return json.loads(await resp.text())
            elif returntype == 'binary':
                return await resp.read()

# the actual scheduler loop 
# async def scheduler():
#     while True:
#         await schedule.run_pending()
#         await asyncio.sleep(1)

if __name__ == '__main__':
    client = SrlBot(c.SRL_NICK, realname=c.SRL_NICK)
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    # loop.create_task(scheduler())
    client.run('irc.speedrunslive.com')
