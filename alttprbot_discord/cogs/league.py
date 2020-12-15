import asyncio
import os
import random
import traceback
import logging

import aiohttp
import discord
from discord.ext import commands, tasks

from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import config, srlnick
from alttprbot.tournament import league
from alttprbot.util import speedgaming
from config import Config as c

from ..util import checks


def restrict_league_server():
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        if ctx.guild.id == int(await config.get(0, 'AlttprLeagueServer')):
            return True

        return False
    return commands.check(predicate)


class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.create_races.start()
        self.find_unsubmitted_races.start()

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
                    await league.create_league_race_room(episode['id'])
                except Exception as e:
                    logging.exception(
                        "Encountered a problem when attempting to create RT.gg race room.")
                    guild_id = await config.get(0, 'AlttprLeagueServer')
                    audit_channel_id = await config.get(guild_id, 'AlttprLeagueAuditChannel')
                    audit_channel = self.bot.get_channel(int(audit_channel_id))
                    if audit_channel:
                        await audit_channel.send(
                            f"@here There was an error while automatically creating a race room for episode `{episode['id']}`.\n\n{str(e)}",
                            allowed_mentions=discord.AllowedMentions(
                                everyone=True)
                        )

        print('done')

    @tasks.loop(minutes=0.25 if c.DEBUG else 240, reconnect=True)
    async def find_unsubmitted_races(self):
        print('scanning for unsubmitted races')
        if c.DEBUG:
            return
            # events = ['test']
        else:
            events = ['alttprleague', 'invleague']

        for event in events:
            try:
                episodes = await speedgaming.get_upcoming_episodes_by_event(event, hours_past=0, hours_future=72)
            except Exception as e:
                logging.exception(
                    "Encountered a problem when attempting to retrieve SG schedule.")
                continue
            for episode in episodes:
                print(episode['id'])
                try:
                    await league.send_race_submission_form(episode['id'])
                except Exception as e:
                    logging.exception(
                        "Encountered a problem when attempting send race submission.")

    @create_races.before_loop
    async def before_create_races(self):
        print('league create_races loop waiting...')
        await self.bot.wait_until_ready()

    @find_unsubmitted_races.before_loop
    async def before_find_unsubmitted_races(self):
        print('league find_unsubmitted_races loop waiting...')
        await self.bot.wait_until_ready()

    @commands.command(
        help='Set the ALTTPR League Week.'
    )
    @commands.has_any_role('Admin', 'Mods', 'Bot Overlord')
    @restrict_league_server()
    async def setleagueweek(self, ctx, week):
        guildid = ctx.guild.id if ctx.guild else 0
        await config.set_parameter(guildid, 'AlttprLeagueWeek', week)

    @commands.command(
        help='Create League RT.gg Race Room.'
    )
    @commands.has_any_role('Admin', 'Mods', 'Bot Overlord')
    @restrict_league_server()
    async def leaguecreate(self, ctx, episodeid: int):
        await league.create_league_race_room(episodeid)

    @commands.command(
        help='Get the league week.'
    )
    @restrict_league_server()
    async def getleagueweek(self, ctx):
        guildid = ctx.guild.id if ctx.guild else 0
        week = await config.get(guildid, 'AlttprLeagueWeek')
        await ctx.send(f"This is Week {week}")

    @commands.command(
        brief='Generate a practice seed.',
        help='Generate a league practice seed for the specified league week.'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def leaguepractice(self, ctx, week: str):
        game_type = league.WEEKDATA[week]['type']
        friendly_name = league.WEEKDATA[week]['friendly_name']
        spoiler_log_url = None

        if game_type == 'preset':
            seed, _ = await preset.get_preset(league.WEEKDATA[week]['preset'], nohints=True, allow_quickswap=True)
        elif game_type == 'mystery':
            seed = await mystery.generate_random_game(weightset=league.WEEKDATA[week]['weightset'], spoilers="mystery", tournament=True)
        elif game_type == 'spoiler':
            seed, _, spoiler_log_url = await spoilers.generate_spoiler_game(league.WEEKDATA[week]['preset'])

        embed = await seed.embed(
            name=f"Practice - {friendly_name}",
            emojis=self.bot.emojis
        )
        if spoiler_log_url:
            embed.insert_field_at(0, name="Spoiler Log URL",
                                  value=spoiler_log_url, inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    @restrict_league_server()
    async def importleaguehelper(self, ctx, user: discord.Member, rtgg_tag):
        async with aiohttp.request(method='get',
                                   url='https://racetime.gg/user/search',
                                   params={'term': rtgg_tag}) as resp:
            results = await resp.json()

        if len(results['results']) > 0:
            for result in results['results']:
                await srlnick.insert_rtgg_id(user.id, result['id'])
        else:
            await ctx.send("Could not map RT.gg tag")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    @restrict_league_server()
    async def importleagueroles(self, ctx):
        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/roster/'
        ) as resp:
            roster = await resp.json()

        pendant_roles = {}
        for pendant in ['courage', 'wisdom', 'power']:
            pendant_roles[pendant] = await find_or_create_role(ctx, pendant)

        for division in roster['divisions']:
            await update_division(ctx, division=division, pendant_roles=pendant_roles)

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    @restrict_league_server()
    async def leagueroles(self, ctx, member_tag):
        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/player/',
            params={
                'discord': member_tag,
            },
            raise_for_status=True
        ) as resp:
            r = await resp.json()
            player = r['results'][0]

        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/team/',
            params={
                'name': player['team_name'],
            },
            raise_for_status=True
        ) as resp:
            r = await resp.json()
            team = r['results'][0]

        pendant = player['position'].lower()
        division_role = await find_or_create_role(ctx, f"Division - {player['division_name']}")
        player_role = await find_or_create_role(
            ctx,
            "Racer" if team['invitational'] else "Open Racer"
        )
        team_role = await find_or_create_role(ctx, player['team_name'])
        pendant_role = await find_or_create_role(ctx, pendant)

        await update_player(
            ctx,
            team=team,
            division_role=division_role,
            player_role=player_role,
            team_role=team_role,
            pendant=pendant,
            pendant_role=pendant_role
        )


async def update_division(ctx, division, pendant_roles):
    division_role = await find_or_create_role(ctx, f"Division - {division['name']}")
    player_role = await find_or_create_role(
        ctx,
        "Racer" if division['invitational'] else "Open Racer"
    )
    for team in division['teams']:
        await update_team(ctx, team, division_role=division_role, player_role=player_role, pendant_roles=pendant_roles)


async def update_team(ctx, team, division_role, player_role, pendant_roles):
    team_role = await find_or_create_role(ctx, team['name'])

    for pendant in ['courage', 'wisdom', 'power']:
        await update_player(ctx, team, division_role, player_role, team_role, pendant, pendant_roles[pendant])


async def update_player(ctx, team, division_role, player_role, team_role, pendant, pendant_role):
    if c.DEBUG:
        await asyncio.sleep(random.uniform(0, 3))
        print(
            f"would have added \"{team[pendant]['discord']}\" to role \"{division_role.name}\"")
        print(
            f"would have added \"{team[pendant]['discord']}\" to role \"{player_role.name}\"")
        print(
            f"would have added \"{team[pendant]['discord']}\" to role \"{team_role.name}\"")
        print(
            f"would have added \"{team[pendant]['discord']}\" to role \"{pendant_role.name}\"")
    else:
        team_member = ctx.guild.get_member_named(
            team[pendant]['discord'])
        if team_member is None:
            await ctx.send(f"Could not resolve user {team[pendant]['discord']}, skipping...")
            return
        await team_member.add_roles(division_role, player_role, team_role, pendant_role)
        await srlnick.insert_twitch_name(team_member.id, team[pendant]['twitch_name'])
        await srlnick.insert_rtgg_id(team_member.id, team[pendant]['rtgg_id'])

        if os.environ.get("LEAGUE_SUBMIT_GAME_SECRET"):
            if not team[pendant].get('discord_id', None) == team_member.id:
                async with aiohttp.request(
                    method='post',
                    url='https://alttprleague.com/json_ep/player/',
                    data={
                        'id': team[pendant]['id'],
                        'discord_id': team_member.id,
                        'secret': os.environ.get("LEAGUE_SUBMIT_GAME_SECRET")
                    }
                ) as _:
                    pass
        else:
            print(
                f"Would have updated \"{team[pendant]['discord']}\" ({team[pendant]['id']}) to discord id {team_member.id}")


async def find_or_create_role(ctx, role_name):
    try:
        role = await commands.RoleConverter().convert(ctx, role_name)
    except commands.RoleNotFound:
        role = await ctx.guild.create_role(name=role_name, reason=f"Created by a importleagueroles command executed by {ctx.author.name}#{ctx.author.discriminator}")

    return role


def setup(bot):
    bot.add_cog(League(bot))
