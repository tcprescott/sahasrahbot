import datetime
import logging
import json

import aiohttp
import dateutil.parser
import discord
import pytz
from alttprbot.util import speedgaming
from alttprbot.database import sgdailies, tournament_results
from discord.ext import commands, tasks
from config import Config as c
from alttprbot_racetime import bot as racetime


class SgDaily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.create_races.start()

    @tasks.loop(minutes=0.25 if c.DEBUG else 5, reconnect=True)
    async def create_races(self):
        active_sgdailies = await sgdailies.get_active_dailies()

        print("scanning SG dailies for races to create")
        for sgdaily in active_sgdailies:
            if not sgdaily['racetime_category'] in racetime.racetime_bots:
                logging.error(f"Racetime Bot is not connected to category {sgdaily['racetime_category']}")
                continue
            try:
                episodes = await speedgaming.get_upcoming_episodes_by_event(sgdaily['slug'], hours_past=1, hours_future=.25)
            except Exception as e:
                logging.exception("Encountered a problem when attempting to retrieve SG schedule.")
                continue
            for episode in episodes:
                print(episode['id'])
                try:
                    rtgg_category = racetime.racetime_bots[sgdaily['racetime_category']]
                    race = await tournament_results.get_active_tournament_race_by_episodeid(episode['id'])

                    if race:
                        async with aiohttp.request(
                                method='get',
                                url=rtgg_category.http_uri(f"/{race['srl_id']}/data"),
                                raise_for_status=True) as resp:
                            race_data = json.loads(await resp.read())
                        status = race_data.get('status', {}).get('value')
                        if not status == 'cancelled':
                            continue
                        await tournament_results.delete_active_tournament_race(race['srl_id'])

                    start_time = datetime.datetime.strptime(episode['when'], "%Y-%m-%dT%H:%M:%S%z")
                    seed_time = start_time - datetime.timedelta(minutes=10)
                    if episode['channels']:
                        broadcast_channels = " on " + ', '.join([a['name'] for a in episode['channels'] if not " " in a['name']])
                    else:
                        broadcast_channels = ""
                    handler = await rtgg_category.startrace(
                        goal=sgdaily['racetime_goal'],
                        invitational=False,
                        unlisted=False,
                        info=sgdaily['race_info'].format(
                            title=episode['match1']['title'],
                            start_time=start_time.astimezone(pytz.timezone('US/Eastern')).strftime("%-I:%M %p"),
                            seed_time=seed_time.astimezone(pytz.timezone('US/Eastern')).strftime("%-I:%M %p"),
                            channel=broadcast_channels
                        ),
                        start_delay=15,
                        time_limit=24,
                        streaming_required=True,
                        auto_start=True,
                        allow_comments=True,
                        hide_comments=True,
                        allow_midrace_chat=True,
                        allow_non_entrant_chat=False,
                        chat_message_delay=0
                    )

                    await tournament_results.insert_tournament_race(
                        srl_id=handler.data.get('name'),
                        episode_id=episode['id'],
                        event=episode['event']['slug']
                    )

                    channel = self.bot.get_channel(sgdaily['announce_channel'])

                    if channel:
                        await channel.send(
                            sgdaily['announce_message'].format(
                                title=episode['match1']['title'],
                                start_time=start_time.astimezone(pytz.timezone('US/Eastern')).strftime("%-I:%M %p"),
                                seed_time=seed_time.astimezone(pytz.timezone('US/Eastern')).strftime("%-I:%M %p"),
                                racetime_url=f"https://racetime.gg{handler.data['url']}",
                                channel=broadcast_channels
                            )
                        )

                except Exception as e:
                    logging.exception("Encountered a problem when attempting to create RT.gg race room.")
                    continue

        print('done')

    @create_races.before_loop
    async def before_create_races(self):
        print('tournament create_races loop waiting...')
        await self.bot.wait_until_ready()

    @commands.command(
        brief="Retrieves the next ALTTPR SG daily race.",
        help="Retrieves the next ALTTPR SG daily race.",
    )
    @commands.cooldown(rate=1, per=900, type=commands.BucketType.channel)
    async def sgdaily(self, ctx, get_next=1):
        sg_schedule = await speedgaming.get_upcoming_episodes_by_event('alttprdaily', hours_past=0, hours_future=192)
        if len(sg_schedule) == 0:
            await ctx.reply("There are no currently SpeedGaming ALTTPR Daily Races scheduled within the next 8 days.")
            return

        if get_next == 1:
            embed = discord.Embed(
                title=sg_schedule[0]['event']['name'],
                description=f"**Mode:** {'*TBD*' if sg_schedule[0]['match1']['title'] == '' else sg_schedule[0]['match1']['title']}\n[Full Schedule](http://speedgaming.org/alttprdaily)"
            )
        else:
            embed = discord.Embed(
                title="ALTTP Randomizer SG Daily Schedule",
                description="[Full Schedule](http://speedgaming.org/alttprdaily)"
            )

        for episode in sg_schedule[0:get_next]:
            when = dateutil.parser.parse(episode['when'])
            when_central = when.astimezone(pytz.timezone(
                'US/Eastern')).strftime('%m-%d %I:%M %p')
            when_europe = when.astimezone(pytz.timezone(
                'Europe/Berlin')).strftime('%m-%d %I:%M %p')
            difference = when - datetime.datetime.now(when.tzinfo)

            if get_next == 1:
                embed.add_field(
                    name='Time', value=f"**US:** {when_central} Eastern\n**EU:** {when_europe} CET/CEST\n\n{round(difference / datetime.timedelta(hours=1), 1)} hours from now", inline=False)
                broadcast_channels = [a['name']
                                      for a in episode['channels'] if not " " in a['name']]
                if broadcast_channels:
                    embed.add_field(name="Twitch Channels", value=', '.join(
                        [f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
            else:
                embed.add_field(
                    name='TBD' if episode['match1']['title'] == '' else episode['match1']['title'],
                    value=(
                        f"**US:** {when_central} Eastern\n"
                        f"**EU:** {when_europe} CET/CEST\n\n"
                    ),
                    inline=False
                )
        embed.set_footer()

        embed.set_thumbnail(
            url='https://pbs.twimg.com/profile_images/1185422684190105600/3jiXIf5Y_400x400.jpg')
        await ctx.reply(embed=embed)


def setup(bot):
    bot.add_cog(SgDaily(bot))
