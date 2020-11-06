import asyncio

import discord
from discord.ext import commands, tasks

from alttprbot.database import config, sgl2020_tournament
from alttprbot.tournament.sgl import create_sgl_match, scan_sgl_schedule, record_episode, race_recording_task
from alttprbot.util import speedgaming
from config import Config as c


def restrict_sgl_server():
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        if ctx.guild.id == int(await config.get(0, 'SpeedGamingLiveGuild')):
            return True

        return False
    return commands.check(predicate)


def restrict_smm2_channel():
    async def predicate(ctx):
        if ctx.guild is None:
            return False

        race = await sgl2020_tournament.get_active_tournament_race(ctx.channel.id)
        if race:
            return True

        return False
    return commands.check(predicate)


class SpeedGamingLive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.create_races.start()
        self.record_races.start()

    @tasks.loop(minutes=0.25 if c.DEBUG else 5, reconnect=True)
    async def create_races(self):
        await scan_sgl_schedule()

    @tasks.loop(minutes=0.25 if c.DEBUG else 15, reconnect=True)
    async def record_races(self):
        await race_recording_task()

    @commands.group()
    @restrict_sgl_server()
    async def sgl(self, ctx):
        pass

    @sgl.command()
    @restrict_sgl_server()
    @commands.has_any_role('Admin', 'Tournament Admin')
    async def create(self, ctx, episode_id: int, force: bool=False):
        episode = await speedgaming.get_episode(episode_id)
        await create_sgl_match(episode, force=force)

    @sgl.command()
    @restrict_sgl_server()
    @restrict_smm2_channel()
    async def smmclose(self, ctx):
        await ctx.send("WARNING:  This room will be closing in 10 seconds.  It will become inaccessible to non-admins.")
        await asyncio.sleep(10)
        smm2_category_id = int(await config.get(ctx.guild.id, 'SGLSMM2CategoryClosed'))
        await ctx.channel.edit(
            sync_permissions=True,
            category=discord.utils.get(
                ctx.guild.categories, id=smm2_category_id)
        )
        race = await sgl2020_tournament.get_active_tournament_race(ctx.channel.id)
        await record_episode(race)

    @sgl.command()
    @restrict_sgl_server()
    @commands.is_owner()
    async def record(self, ctx, episode_id):
        race = await sgl2020_tournament.get_tournament_race_by_episodeid(episode_id)
        await record_episode(race)


def setup(bot):
    bot.add_cog(SpeedGamingLive(bot))
