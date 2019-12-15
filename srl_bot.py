import argparse
import asyncio
import json
import math
import re
import shlex
import sys
import time

import aiohttp
import ircmessage
# import aioschedule as schedule
import pydle
from quart import abort, jsonify, request
from quart_openapi import Pint, Resource

from alttprbot.alttprgen import preset, mystery, spoilers
from alttprbot.database import spoiler_races, srl_races
from alttprbot.smz3gen import preset as smz3_preset
from alttprbot.smz3gen import spoilers as smz3_spoilers
from alttprbot.util import orm
from config import Config as c

import alttprbot_srl.commands

starting = re.compile("\\x034\\x02The race will begin in 10 seconds!\\x03\\x02")
go = re.compile("\\x034\\x02GO!\\x03\\x02")
newroom = re.compile("Race initiated for (.*)\. Join\\x034 (#srl-[a-z0-9]{5}) \\x03to participate\.")
runnerdone = re.compile("(.*) (has forfeited from the race\.|has finished in .* place with a time of [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.)")

srl_game_whitelist = [
    'The Legend of Zelda: A Link to the Past Hacks',
    'A Link to the Past & Super Metroid Combo Randomizer'
]

class SrlBot(pydle.Client):
    async def on_connect(self):
        await self.message('NickServ', 'identify ' + c.SRL_PASSWORD)
        await self.join('#speedrunslive')
        await self.join('#alttpr')

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
            if result and result.group(1) in srl_game_whitelist:
                if not c.DEBUG:
                    await asyncio.sleep(1)
                    await self.join(result.group(2))
                    await asyncio.sleep(60)
                    await self.message(result.group(2), "Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR/SMZ3 seed roller.  To see what I can do, visit https://sahasrahbot.synack.live")
                else:
                    print(f'would have joined {result.group(2)}')

        if target.startswith('#srl-') and (source == 'RaceBot' or source == 'synack'):
            if starting.match(message) or message=='$test starting':
                srl_id = srl_race_id(target)
                race = await srl_races.get_srl_race_by_id(srl_id)
                if race:
                    if not client.in_channel(target):
                        await client.join(target)
                    await client.message(target, f".setgoal {race['goal']}")
                    await srl_races.delete_srl_race(srl_id)

            if go.match(message) or message=='$test go':
                srl_id = srl_race_id(target)

                await request_json_post(
                    'http://localhost:5001/api/srl/start',
                    data = {
                        'auth': c.InternalApiToken,
                        'raceid': srl_id
                    },
                    returntype=json
                )

                # spoilers
                race = await spoiler_races.get_spoiler_race_by_id(srl_id)
                if race:
                    await self.message(target, 'Sending spoiler log...')
                    await self.message(target, '---------------')
                    await self.message(target, f"This race\'s spoiler log: {race['spoiler_url']}")
                    await self.message(target, '---------------')
                    await self.message(target, 'GLHF! :mudora:')
                    await countdown_timer(
                        ircbot=self,
                        duration_in_seconds=race['studytime'],
                        srl_channel=target,
                        loop=loop,
                        beginmessage=True,
                    )
                    await spoiler_races.delete_spoiler_race(srl_id)

            result = runnerdone.search(message)
            if result:
                await request_json_post(
                    'http://localhost:5001/api/srl/finish',
                    data = {
                        'auth': c.InternalApiToken,
                        'nick': result.group(1)
                    },
                    returntype=json
                )


        # Handle any messages that start with $
        if not message[0] == '$': return

        try:
            args = alttprbot_srl.commands.parse_args(message)
        except argparse.ArgumentError as e:
            if not target == '#speedrunslive':
                await self.message(target, e.message)
            return

        if args.command == '$preset' and target.startswith('#srl-'):
            srl_id = srl_race_id(target)
            srl = await get_race(srl_id)
            await self.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
            race = await srl_races.get_srl_race_by_id(srl_id)

            if race:
                await self.message(target, "There is already a game generated for this room.  To cancel it, use the $cancel command.")
                return

            if srl['game']['abbrev'] == 'alttphacks':
                try:
                    seed, preset_dict = await preset.get_preset(args.preset, hints=args.hints, spoilers="off")
                except preset.PresetNotFoundException:
                    await self.message(target, "That preset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live")

                goal_name = preset_dict['goal_name']
                goal = f"vt8 randomizer - {goal_name}"
                code = await seed.code()
                if args.silent:
                    await self.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
                else:
                    await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
            elif srl['game']['abbrev'] == 'alttpsm':
                seed = await smz3_preset.get_preset(args.preset)
                goal = 'beat the games'
                if args.silent:
                    await self.message(target, f"{goal} - {args.preset} - {seed.url}")
                else:
                    await self.message(target, f".setgoal {goal} - {args.preset} - {seed.url}")
            else:
                await self.message(target, "This game is not yet supported.")
                return

            await srl_races.insert_srl_race(srl_id, goal)

        if args.command == '$random' and target.startswith('#srl-'):
            srl_id = srl_race_id(target)
            srl = await get_race(srl_id)
            await self.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
            race = await srl_races.get_srl_race_by_id(srl_id)

            if race:
                await self.message(target, "There is already a game generated for this room.  To cancel it, use the $cancel command.")
                return

            if srl['game']['abbrev'] == 'alttphacks':
                try:
                    seed = await mystery.generate_random_game(weightset=args.weightset, tournament=True, spoilers="off")
                except mystery.WeightsetNotFoundException:
                    await self.message(target, "That weightset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live")
                    return

                code = await seed.code()
                goal = f"vt8 randomizer - random {args.weightset}"
                if args.silent:
                    await self.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
                else:
                    await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
            else:
                await self.message(target, "This game is not yet supported.")
                return

            await srl_races.insert_srl_race(srl_id, goal)

        if args.command == '$mystery' and target.startswith('#srl-'):
            srl_id = srl_race_id(target)
            srl = await get_race(srl_id)
            await self.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
            race = await srl_races.get_srl_race_by_id(srl_id)

            if race:
                await self.message(target, "There is already a game generated for this room.  To cancel it, use the $cancel command.")
                return

            if srl['game']['abbrev'] == 'alttphacks':
                try:
                    seed = await mystery.generate_random_game(weightset=args.weightset, tournament=True, spoilers="mystery")
                except mystery.WeightsetNotFoundException:
                    await self.message(target, "That weightset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live")
                    return

                code = await seed.code()
                goal = f"vt8 randomizer - mystery {args.weightset}"
                if args.silent:
                    await self.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
                else:
                    await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
            else:
                await self.message(target, "This game is not yet supported.")
                return

            await srl_races.insert_srl_race(srl_id, goal)

        if args.command == '$custom' and target.startswith('#srl-'):
            await self.message(target, "Not yet implemented.  Sorry!")

        if args.command == '$spoiler' and target.startswith('#srl-'):
            srl_id = srl_race_id(target)
            srl = await get_race(srl_id)
            await self.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
            race = await srl_races.get_srl_race_by_id(srl_id)

            if race:
                await self.message(target, "There is already a game generated for this room.  To cancel it, use the $cancel command.")
                return

            if srl['game']['abbrev'] == 'alttphacks':
                try:
                    seed, preset_dict, spoiler_log_url = await spoilers.generate_spoiler_game(args.preset)
                except preset.PresetNotFoundException:
                    await self.message(target, "That preset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live")

                goal_name = preset_dict['goal_name']

                if not seed:
                    return

                goal = f"vt8 randomizer - spoiler {goal_name}"
                studytime = 900 if not args.studytime else args.studytime 
                code = await seed.code()
                if args.silent:
                    await self.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
                else:
                    await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
                await self.message(target, f"The spoiler log for this race will be sent after the race begins in SRL.  A {studytime}s countdown timer at that time will begin.")
            elif srl['game']['abbrev'] == 'alttpsm':
                seed, spoiler_log_url = await smz3_spoilers.generate_spoiler_game(args.preset)

                if seed is None:
                    await self.message(target, "That preset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live")
                    return

                goal = f"spoiler beat the games"
                studytime = 1500 if not args.studytime else args.studytime 
                if args.silent:
                    await self.message(target, f"{goal} - {seed.url}")
                else:
                    await self.message(target, f".setgoal {goal} - {seed.url}")
                await self.message(target, f"The spoiler log for this race will be sent after the race begins in SRL.  A {studytime}s countdown timer at that time will begin.")
            else:
                await self.message(target, "This game is not yet supported.")
                return

            await srl_races.insert_srl_race(srl_id, goal)
            await spoiler_races.insert_spoiler_race(srl_id, spoiler_log_url, studytime)

        if args.command == '$cancel' and target.startswith('#srl-'):
            srl_id = srl_race_id(target)
            await srl_races.delete_srl_race(srl_id)
            await spoiler_races.delete_spoiler_race(srl_id)
            await self.message(target, "Current race cancelled.")
            await self.message(target, f".setgoal new race")

        if args.command == '$help' and target.startswith('#srl-'):
            await self.message(target, "For documentation on using this bot, visit https://sahasrahbot.synack.live")

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


async def countdown_timer(ircbot, duration_in_seconds, srl_channel, loop, beginmessage=False):
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

# the actual scheduler loop 
# async def scheduler():
#     while True:
#         await schedule.run_pending()
#         await asyncio.sleep(1)

# small restful API server running locally so my other bots can send messages

app = Pint(__name__, title='Srl Bot API')

@app.route('/api/message')
class Message(Resource):
    async def post(self):
        data = await request.get_json()
        if 'auth' in data and data['auth'] == c.InternalApiToken:
            if not client.in_channel(data['channel']):
                abort(400, "Bot not in specified channel")
            result = await client.message(data['channel'], data['message'])
            return jsonify({"success": True})
        else:
            abort(401)

if __name__ == '__main__':
    client = SrlBot(c.SRL_NICK, realname=c.SRL_NICK)
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))

    loop.create_task(client.connect('irc.speedrunslive.com'))
    loop.create_task(app.run(host='127.0.0.1', port=5000, loop=loop))
    loop.run_forever()
