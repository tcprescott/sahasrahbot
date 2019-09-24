import pydle
import shlex
import re
from config import Config as c

from alttprbot.util import orm

from alttprbot.database import alttprgen
from alttprbot.database import srl_races

from alttprbot.alttprgen.weights import weights
from alttprbot.alttprgen.random import generate_random_game
from alttprbot.alttprgen.preset import get_preset

import asyncio
import argparse

class SrlBot(pydle.Client):
    async def on_connect(self):
        await self.message('NickServ', 'identify ' + c.SRL_PASSWORD)
        await self.join('#speedrunslive')

    # target = channel of the message
    # source = sendering of the message
    # message = the message, duh
    async def on_message(self, target, source, message):
        print('MESSAGE: ' + target + ' - ' + source + ' - ' + message) #dumb debugging message

        # filter messages sent by the bot (we do not want to react to these)
        if source == c.SRL_NICK:
            return
        if not message[0] == '$':
            return
        
        split_msg = ['sb'] + shlex.split(message)

        parser = argparse.ArgumentParser()
        parser.add_argument('base', type=str)

        subparsers = parser.add_subparsers(dest="command")

        parser_preset = subparsers.add_parser('$preset')
        parser_preset.add_argument('preset')

        parser_spoiler = subparsers.add_parser('$spoiler')

        parser_random = subparsers.add_parser('$random')
        parser_random.add_argument('weightset', nargs='?', default="weighted")

        parser_join = subparsers.add_parser('$join')
        parser_join.add_argument('channel')

        args = parser.parse_args(split_msg)
        print(args)

        if args.command == '$preset' and target.startswith('#srl-'):
            await self.message(target, "Generating game, please wait.")
            srl_id = srl_race_id(target)
            seed, goal_name = await get_preset(args.preset)
            if not seed:
                await self.message(target, "That preset does not exist.")
                return
            goal = f"vt8 randomizer - {goal_name}"
            code = await seed.code()
            await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
            await srl_races.insert_srl_race(srl_id, goal)

        if args.command == '$random' and target.startswith('#srl-'):
            await self.message(target, "Generating game, please wait.")
            srl_id = srl_race_id(target)
            seed = await generate_random_game(logic='NoGlitches', weightset=args.weightset, tournament=True)
            code = await seed.code()
            goal = f"vt8 randomizer - random {args.weightset}"
            await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
            await srl_races.insert_srl_race(srl_id, goal)

        if args.command == '$spoiler' and target.startswith('#srl-'):
            await self.message(target, "Not yet implemented.  Sorry!")

        if args.command == '$join':
            await self.join(args.channel)

    # target = you
    # source = sendering of the message
    # message = the message, duh
    async def on_notice(self, target, source, message):
        print('NOTICE: ' + target + ' - ' + source + ' - ' + message) #dumb debugging message
        if message == 'Password accepted - you are now recognized.':
            await asyncio.sleep(1)
            await self.join('#srl-xgz3y')

def srl_race_id(channel):
    if re.search('^#srl-[a-z0-9]{5}$',channel):
        return channel.partition('-')[-1]

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    client = SrlBot(c.SRL_NICK, realname=c.SRL_NICK)
    client.run('irc.speedrunslive.com')