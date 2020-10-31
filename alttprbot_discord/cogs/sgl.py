import random
import string

from alttprbot.alttprgen import randomizer
from alttprbot.database import config
from alttprbot_racetime.bot import racetime_bots
from discord.ext import commands, tasks
from alttprbot.util import speedgaming
from config import Config as c  # pylint: disable=no-name-in-module
from alttprbot.tournament.sgl import create_sgl_race_room
import logging
import discord

def restrict_sgl_server():
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        if ctx.guild.id == int(await config.get(0, 'SpeedGamingLiveGuild')):
            return True

        return False
    return commands.check(predicate)

class SpeedGamingLive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.create_races.start()

    @tasks.loop(minutes=0.25 if c.DEBUG else 5, reconnect=True)
    async def create_races(self):
        if c.DEBUG:
            return
            # events = ['test']
        else:
            events = ['alttprleague', 'invleague']
        print("scanning SG schedule for races to create")
        for event in events:
            try:
                episodes = await speedgaming.get_upcoming_episodes_by_event(event, hours_past=0.5, hours_future=.75)
            except Exception as e:
                logging.exception(
                    "Encountered a problem when attempting to retrieve SG schedule.")
                continue
            for episode in episodes:
                print(episode['id'])
                try:
                    await create_sgl_race_room(episode['id'])
                except Exception as e:
                    logging.exception(
                        "Encountered a problem when attempting to create RT.gg race room.")
                    guild_id = await config.get(0, 'SGLAuditChannel')
                    audit_channel_id = await config.get(guild_id, 'SGLAuditChannel')
                    audit_channel = self.bot.get_channel(int(audit_channel_id))
                    if audit_channel:
                        await audit_channel.send(
                            f"@here There was an error while automatically creating a race room for episode `{episode['id']}`.\n\n{str(e)}",
                            allowed_mentions=discord.AllowedMentions(
                                everyone=True)
                        )

        print('done')


def setup(bot):
    bot.add_cog(SpeedGamingLive(bot))
