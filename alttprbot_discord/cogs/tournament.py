import csv
import datetime
import io
import logging

import aiohttp
import discord
import pytz
from discord.ext import commands, tasks

from alttprbot.database import config, srlnick, tournaments
from alttprbot.exceptions import SahasrahBotException
from alttprbot.tournament import alttpr
from alttprbot.util import speedgaming
from config import Config as c

# this module was only intended for the Main Tournament 2019
# we will probably expand this later to support other tournaments in the future


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.create_races.start()
        self.record_races.start()
        self.scheduling_needs.start()

    @tasks.loop(minutes=0.25 if c.DEBUG else 5, reconnect=True)
    async def create_races(self):
        active_tournaments = await tournaments.get_active_tournaments()

        logging.info("scanning SG schedule for tournament races to create")
        for tournament in active_tournaments:
            try:
                episodes = await speedgaming.get_upcoming_episodes_by_event(tournament['slug'], hours_past=0.5, hours_future=.75)
            except Exception as e:
                logging.exception(
                    "Encountered a problem when attempting to retrieve SG schedule.")
                continue
            for episode in episodes:
                logging.info(episode['id'])
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

        logging.info('done')

    @tasks.loop(minutes=0.25 if c.DEBUG else 15, reconnect=True)
    async def scheduling_needs(self):
        active_tournaments = await tournaments.get_active_tournaments()

        logging.info("scanning SG schedule for tournament races to create")
        for tournament in active_tournaments:
            if tournament.get('scheduling_needs_channel_id', None) is None:
                continue

            try:
                episodes = await speedgaming.get_upcoming_episodes_by_event(tournament['slug'], hours_past=0, hours_future=48)
            except Exception as e:
                logging.exception("Encountered a problem when attempting to retrieve SG schedule.")
                continue

            scheduling_needs_channel = self.bot.get_channel(tournament.get('scheduling_needs_channel_id', None))

            comms_needed = []
            trackers_needed = []
            broadcasters_needed = []

            lang = tournament.get('lang', 'en')
            if lang is None:
                lang = 'en'

            for episode in episodes:
                broadcast_channels = [c['name'] for c in episode['channels'] if c['id'] not in [0, 31, 36, 62, 63, 64, 65] and c['language'] == lang]
                if not broadcast_channels:
                    continue

                start_time = datetime.datetime.strptime(episode['when'], "%Y-%m-%dT%H:%M:%S%z")
                if lang == 'en':
                    start_time_string = start_time.astimezone(pytz.timezone('US/Eastern')).strftime("%m/%d %-I:%M %p") + " Eastern"
                elif lang == 'de':
                    start_time_string = start_time.astimezone(pytz.timezone('Europe/Berlin')).strftime("%m/%d %H:%M %p") + " European"

                commentators_approved = [p for p in episode['commentators'] if p['approved'] and p['language'] == lang]

                if (c_needed := 2 - len(commentators_approved)) > 0:
                    comms_needed += [f"*{start_time_string}* - Need **{c_needed}** - [Sign Up!](http://speedgaming.org/commentator/signup/{episode['id']}/)"]

                trackers_approved = [p for p in episode['trackers'] if p['approved'] and p['language'] == lang]

                if (t_needed := 1 - len(trackers_approved)) > 0:
                    trackers_needed += [f"*{start_time_string}* - Need **{t_needed}** - [Sign Up!](http://speedgaming.org/tracker/signup/{episode['id']}/)"]

                if broadcast_channels[0] in ['ALTTPRandomizer', 'ALTTPRandomizer2', 'ALTTPRandomizer3', 'ALTTPRandomizer4', 'ALTTPRandomizer5', 'ALTTPRandomizer6']:
                    broadcasters_approved = [p for p in episode['broadcasters'] if p['approved'] and p['language'] == lang]

                    if (b_needed := 1 - len(broadcasters_approved)) > 0:
                        broadcasters_needed += [f"*{start_time_string}* - Need **{b_needed}** - [Sign Up!](http://speedgaming.org/broadcaster/signup/{episode['id']}/)"]

            embed = discord.Embed(
                title="Scheduling Needs",
                description="This is the current scheduling needs for the next 48 hours.",
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(
                name="Commentators Needed",
                value="\n".join(comms_needed) if comms_needed else "No current needs.",
                inline=False
            )
            if tournament.get('scheduling_needs_tracker', None):
                embed.add_field(
                    name="Trackers Needed",
                    value="\n".join(trackers_needed) if trackers_needed else "No current needs.",
                    inline=False
                )
            if broadcasters_needed:
                embed.add_field(
                    name="Broadcasters Needed",
                    value="\n".join(broadcasters_needed),
                    inline=False
                )

            try:
                bot_message = False
                async for message in scheduling_needs_channel.history(limit=50):
                    if message.author == self.bot.user:
                        bot_message = True
                        scheduling_needs_message = message
                        await scheduling_needs_message.edit(embed=embed)
                        break

                if not bot_message:
                    await scheduling_needs_channel.send(embed=embed)
            except Exception:
                logging.exception("Unable to update scheduling needs channel.")
                continue

    @tasks.loop(minutes=0.25 if c.DEBUG else 15, reconnect=True)
    async def record_races(self):
        try:
            logging.info("recording tournament races")
            await alttpr.race_recording_task()
            logging.info("done recording")
        except Exception:
            logging.exception("error recording")

    @create_races.before_loop
    async def before_create_races(self):
        logging.info('tournament create_races loop waiting...')
        await self.bot.wait_until_ready()

    @record_races.before_loop
    async def before_record_races(self):
        logging.info('tournament record_races loop waiting...')
        await self.bot.wait_until_ready()

    @scheduling_needs.before_loop
    async def before_scheduling_needs(self):
        logging.info('tournament scheduling_needs loop waiting...')
        await self.bot.wait_until_ready()

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if ctx.guild is None:
            return False

        if await ctx.guild.config_get('TournamentEnabled') == 'true':
            return True
        else:
            return False

    @commands.command(
        help="Generate a tournament race."
    )
    @commands.is_owner()
    async def tourneyrace(self, ctx, episode_number: int, category: str, goal: str):
        await alttpr.create_tournament_race_room(episode_number, category, goal)

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

    @commands.command()
    @commands.is_owner()
    async def importcsv(self, ctx, mode="dry"):
        if not ctx.message.attachments:
            raise SahasrahBotException("You must supply a valid csv file.")

        content = await ctx.message.attachments[0].read()
        role_import_list = csv.DictReader(io.StringIO(content.decode()))
        for i in role_import_list:
            rtgg_tag = i['racetime']
            try:
                user = await commands.MemberConverter().convert(ctx, i['discord'])
            except Exception as e:
                await ctx.reply(f"Could not import {i['discord']}")
                continue
            twitch = i['twitch']

            async with aiohttp.request(method='get',
                                       url='https://racetime.gg/user/search',
                                       params={'term': rtgg_tag}) as resp:
                results = await resp.json()

            if len(results['results']) > 0:
                for result in results['results']:
                    if mode != "dry":
                        await srlnick.insert_rtgg_id(user.id, result['id'])
            else:
                await ctx.reply(f"Could not map RT.gg tag for record {i['discord']}")

            if mode != "dry" and twitch != "":
                await srlnick.insert_twitch_name(user.id, twitch)


def setup(bot):
    bot.add_cog(Tournament(bot))
