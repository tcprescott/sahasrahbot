import asyncio
import random
import os

import aiohttp
from alttprbot.database import config, srlnick
from alttprbot.tournament.league import WEEKDATA, create_league_race_room
from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.util import speedgaming
from config import Config as c  # pylint: disable=no-name-in-module
from discord.ext import commands

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
        await create_league_race_room(episodeid)

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
        game_type = WEEKDATA[week]['type']
        friendly_name = WEEKDATA[week]['friendly_name']
        spoiler_log_url = None

        if game_type == 'preset':
            seed, _ = await preset.get_preset(WEEKDATA[week]['preset'], nohints=True, allow_quickswap=True)
        elif game_type == 'mystery':
            seed = await mystery.generate_random_game(weightset=WEEKDATA[week]['weightset'], spoilers="mystery", tournament=True)
        elif game_type == 'spoiler':
            seed, _, spoiler_log_url = await spoilers.generate_spoiler_game(WEEKDATA[week]['preset'])

        embed = await seed.embed(
            name=f"Practice - {friendly_name}",
            emojis=self.bot.emojis
        )
        if spoiler_log_url:
            embed.insert_field_at(0, name="Spoiler Log URL",
                                  value=spoiler_log_url, inline=False)
        await ctx.send(embed=embed)

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
    @restrict_league_server()
    @commands.is_owner()
    async def leaguetestschedule(self, ctx):
        episodes = await speedgaming.get_upcoming_episodes_by_event('test', hours_past=0, hours_future=.75)
        for episode in episodes:
            await create_league_race_room(episode['id'])

async def update_division(ctx, division, pendant_roles):
    division_role = await find_or_create_role(ctx, f"Division - {division['name']}")
    player_role = await find_or_create_role(
        ctx,
        "Racer" if division['invitational'] else "Open Racer"
    )
    for team in division['teams']:
        team_role = await find_or_create_role(ctx, team['name'])

        for pendant in ['courage', 'wisdom', 'power']:
            if c.DEBUG:
                await asyncio.sleep(random.uniform(0, 3))
                print(
                    f"would have added \"{team[pendant]['discord']}\" to role \"{division_role.name}\"")
                print(
                    f"would have added \"{team[pendant]['discord']}\" to role \"{player_role.name}\"")
                print(
                    f"would have added \"{team[pendant]['discord']}\" to role \"{team_role.name}\"")
                print(
                    f"would have added \"{team[pendant]['discord']}\" to role \"{pendant_roles[pendant].name}\"")
            else:
                team_member = ctx.guild.get_member_named(
                    team[pendant]['discord'])
                if team_member is None:
                    await ctx.send(f"Could not resolve user {team[pendant]['discord']}, skipping...")
                    continue
                await team_member.add_roles(division_role, player_role, team_role, pendant_roles[pendant])
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
