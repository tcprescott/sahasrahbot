import asyncio
import datetime
import aiofiles
import logging

import pydle

from alttprbot.database import srl_races
from alttprbot.exceptions import SahasrahBotException
from alttprbot.util.srl import get_all_races, get_race
from alttprbot_srl import commands, racebot
from config import Config as c


class SrlBot(pydle.Client):
    async def on_connect(self):
        await self.message('NickServ', 'identify ' + c.SRL_PASSWORD)
        await self.join('#speedrunslive')
        await self.join('#alttpr')
#        await self.join_active_races(['alttphacks', 'alttpsm'])
#        await self.process_active_races()
        if c.DEBUG:
            await self.join('#srl-synack-testing')

    # target = channel of the message
    # source = sendering of the message
    # message = the message, duh
    async def on_message(self, target, source, message):
        try:
            await message_logger("MSG", target, source, message)

            # filter messages sent by the bot (we do not want to react to these)
            if source == c.SRL_NICK:
                return

            # handle messages from racebot
            await racebot.handler(target=target, source=source, message=message, client=self)
            # handle user commands
            await commands.handler(target=target, source=source, message=message, client=self)
        except Exception as err:
            await self.message(target, f'{type(err)}: "{str(err)}".  Please contact Synack if this condition persists.')
            if not isinstance(err, SahasrahBotException):
                raise

    # target = you
    # source = sendering of the message
    # message = the message, duh
    async def on_notice(self, target, source, message):
        await message_logger("NOTICE", target, source, message)

        # do stuff that we want after getting recognized by NickServ
        if message == 'Password accepted - you are now recognized.':
            await asyncio.sleep(1)
        #     await self.join('#speedrunslive')
        #     await self.join('#alttpr')
            await self.join_active_races(['alttphacks', 'alttpsm', 'supermetroidhacks', 'supermetroid'])
            await self.process_active_races()
        #     if c.DEBUG: await self.join('#srl-synack-testing')

    async def on_join(self, channel, user):
        await message_logger("JOIN", channel, user, "Joined channel.")

    async def on_part(self, channel, user, message):
        await message_logger("PART", channel, user, message)

    async def on_kick(self, channel, target, by, reason=None):
        await message_logger("KICK", channel, target, f"Kicked by {by} for reason {reason}")

    async def on_kill(self, target, by, reason):
        await message_logger("KILL", target, by, f"Killed for reason {reason}")

    async def on_mode_change(self, channel, modes, by):
        await message_logger("MODE", channel, by, f'Gave {modes[0]} to {modes[1]}')

    async def on_topic_change(self, channel, message, by):
        await message_logger("TOPIC", channel, by, message)
        await racebot.topic_change_handler(channel, by, message, client=self)

    async def join_active_races(self, games):
        races = await get_all_races()
        for race in races['races']:
            if race['game']['abbrev'] in games:
                race_id = race['id']
                if not self.in_channel(f'#srl-{race_id}'):
                    if c.DEBUG:
                        logging.info(f'would have joined #srl-{race_id}')
                    else:
                        await self.join(f'#srl-{race_id}')

    async def process_active_races(self):
        logging.info('process active races running')
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


async def message_logger(msgtype, target, source, message):
    # redact passwords from logs
    try:
        message = message.replace(c.SRL_PASSWORD, '**********')
    except AttributeError:
        pass

    # write event to channel log

    msg = f'{datetime.datetime.now()} - {msgtype} - {target} - {source} - "{message}"\n'
    if target == c.SRL_NICK:
        fileloc = f'/var/log/sahasrahbot/srl/{source}.txt'
    else:
        fileloc = f'/var/log/sahasrahbot/srl/{target}.txt'

    async with aiofiles.open(fileloc, mode='a+') as logfile:
        await logfile.write(msg)


srlbot = SrlBot(c.SRL_NICK, realname=c.SRL_NICK)
