import asyncio
import sys

# import aioschedule as schedule
import pydle
from quart import abort, jsonify, request
from quart_openapi import Pint, Resource

from alttprbot.database import srl_races
from alttprbot.util import orm
from alttprbot.util.srl import get_all_races, get_race
from alttprbot_srl import commands, racebot
from config import Config as c


class SrlBot(pydle.Client):
    async def on_connect(self):
        await self.message('NickServ', 'identify ' + c.SRL_PASSWORD)
        await asyncio.sleep(1)
        await self.join('#speedrunslive')
        await self.join('#alttpr')
        await self.join_active_races(['alttphacks', 'alttpsm'])
        await self.process_active_races()
        if c.DEBUG:
            await self.join('#srl-synack-testing')

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

        # handle messages from racebot
        await racebot.handler(target=target, source=source, message=message, client=self)

        try:
            # handle user commands
            await commands.handler(target=target, source=source, message=message, client=self)
        except Exception as err:
            await self.message(target, f'Error {type(err)}: "{str(err)}".  Please contact Synack if this condition persists.')
            raise err

    # target = you
    # source = sendering of the message
    # message = the message, duh

    async def on_notice(self, target, source, message):
        print('NOTICE: ' + target + ' - ' + source +
              ' - ' + message)  # dumb debugging message

        # do stuff that we want after getting recognized by NickServ
        # if message == 'Password accepted - you are now recognized.':
        #     await asyncio.sleep(1)
        #     await self.join('#speedrunslive')
        #     await self.join('#alttpr')
        #     await self.join_active_races(['alttphacks', 'alttpsm'])
        #     await self.process_active_races()
        #     if c.DEBUG: await self.join('#srl-synack-testing')

    async def join_active_races(self, games):
        races = await get_all_races()
        for race in races['races']:
            if race['game']['abbrev'] in games:
                race_id = race['id']
                if not self.in_channel(f'#srl-{race_id}'):
                    if c.DEBUG:
                        print(f'would have joined #srl-{race_id}')
                    else:
                        await self.join(f'#srl-{race_id}')

    async def process_active_races(self):
        print('process active races running')
        active_races = await srl_races.get_srl_races()
        for active_race in active_races:
            race = await get_race(active_race['srl_id'])
            channel_name = f"#srl-{active_race['srl_id']}"
            if not race:
                await srl_races.delete_srl_race(active_race['srl_id'])
            elif not race['state'] == 1:
                if not self.in_channel(channel_name):
                    await self.join(channel_name)
                await self.message(channel_name, f".setgoal {active_race['goal']}")
                await srl_races.delete_srl_race(active_race['srl_id'])


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
