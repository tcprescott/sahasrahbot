import asyncio

from alttprbot.util import orm
from config import Config as c
from alttprbot_discord.bot import discordbot
from alttprbot_srl.bot import srlbot
from alttprbot_twitch.bot import twitchbot

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    loop.create_task(discordbot.start(c.DISCORD_TOKEN))
    loop.create_task(srlbot.connect('irc.speedrunslive.com'))
    loop.create_task(twitchbot.run())
    loop.run_forever()
