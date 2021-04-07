import logging

import aiohttp
import discord
from discord.ext import commands, tasks

from alttprbot.database import config, srlnick, tournaments
from alttprbot.util import speedgaming
from alttprbot.tournament import alttpr
from config import Config as c


# this module was only intended for the Main Tournament 2019
# we will probably expand this later to support other tournaments in the future


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.create_races.start()

    @tasks.loop(minutes=0.25 if c.DEBUG else 5, reconnect=True)
    async def create_races(self):
        active_tournaments = await tournaments.get_active_tournaments()

        print("scanning SG schedule for tournament races to create")
        for tournament in active_tournaments:
            try:
                episodes = await speedgaming.get_upcoming_episodes_by_event(tournament['slug'], hours_past=0.5, hours_future=.75)
            except Exception as e:
                logging.exception(
                    "Encountered a problem when attempting to retrieve SG schedule.")
                continue
            for episode in episodes:
                print(episode['id'])
                try:
                    await alttpr.create_tournament_race_room(episode['id'], tournament['category'], tournament['goal'])
                except Exception as e:
                    logging.exception(
                        "Encountered a problem when attempting to create RT.gg race room.")
                    audit_channel_id = tournament['audit_channel_id']
                    audit_channel = self.bot.get_channel(audit_channel_id)
                    if audit_channel:
                        await audit_channel.send(
                            f"There was an error while automatically creating a race room for episode `{episode['id']}`.\n\n{str(e)}",
                            allowed_mentions=discord.AllowedMentions(
                                everyone=True)
                        )

        print('done')

    @create_races.before_loop
    async def before_create_races(self):
        print('tournament create_races loop waiting...')
        await self.bot.wait_until_ready()

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if ctx.guild is None:
            return False

        if await config.get(ctx.guild.id, 'TournamentEnabled') == 'true':
            return True
        else:
            return False

    @commands.command(
        help="Generate a tournament race."
    )
    async def tourneyrace(self, ctx, episode_number: int):
        await alttpr.create_tournament_race_room(episode_number)

    @commands.command()
    @commands.is_owner()
    async def importhelper(self, ctx, user: discord.Member, rtgg_tag, twitch=None):
        async with aiohttp.request(method='get',
                                   url='https://racetime.gg/user/search',
                                   params={'term': rtgg_tag}) as resp:
            results = await resp.json()

        if len(results['results']) > 0:
            for result in results['results']:
                await srlnick.insert_rtgg_id(user.id, result['id'])
        else:
            await ctx.reply("Could not map RT.gg tag")

        await srlnick.insert_twitch_name(user.id, twitch)


def setup(bot):
    bot.add_cog(Tournament(bot))
