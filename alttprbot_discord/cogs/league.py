import asyncio
import random

import aiohttp
from alttprbot.database import config, srlnick
from alttprbot.exceptions import SahasrahBotException
from config import Config as c  # pylint: disable=no-name-in-module
from discord.ext import commands


class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx): # pylint: disable=invalid-overridden-method
        if ctx.guild is None:
            return False
        if ctx.guild.id == int(await config.get(0, 'AlttprLeagueServer')):
            return True

        return False

    @commands.command(
        help='Set the ALTTPR League Week.'
    )
    @commands.has_any_role('Admin', 'Mods', 'Bot Overlord')
    async def setleagueweek(self, ctx, week):
        guildid = ctx.guild.id if ctx.guild else 0
        await config.set_parameter(guildid, 'AlttprLeagueWeek', week)

    @commands.command(
        help='Get the league week.'
    )
    async def getleagueweek(self, ctx):
        guildid = ctx.guild.id if ctx.guild else 0
        week = await config.get(guildid, 'AlttprLeagueWeek')
        await ctx.send(f"This is Week {week}")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    async def importleagueroles(self, ctx):

        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/roster/'
        ) as resp:
            roster = await resp.json()

        pendant_roles = {}
        for pendant in ['courage', 'wisdom', 'power']:
            pendant_roles[pendant] = await find_or_create_role(ctx, pendant)

        division_funcs = []
        for division in roster['divisions']:
            # division_funcs.append(update_division(ctx, division=division, pendant_roles=pendant_roles))
            await update_division(ctx, division=division, pendant_roles=pendant_roles)

        # await asyncio.gather(*division_funcs)

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
                print(f"would have added \"{team[pendant]['discord']}\" to role \"{division_role.name}\"")
                print(f"would have added \"{team[pendant]['discord']}\" to role \"{player_role.name}\"")
                print(f"would have added \"{team[pendant]['discord']}\" to role \"{team_role.name}\"")
                print(f"would have added \"{team[pendant]['discord']}\" to role \"{pendant_roles[pendant].name}\"")
            else:
                team_member = ctx.guild.get_member_named(team[pendant]['discord'])
                if team_member is None:
                    await ctx.send(f"Could not resolve user {team[pendant]['discord']}, skipping...")
                    continue
                await team_member.add_roles(division_role, player_role, team_role, pendant_roles[pendant])
                await srlnick.insert_twitch_name(team_member.id, team[pendant]['twitch_name'])

async def find_or_create_role(ctx, role_name):
    try:
        role = await commands.RoleConverter().convert(ctx, role_name)
    except commands.RoleNotFound:
        role = await ctx.guild.create_role(name=role_name, reason=f"Created by a importleagueroles command executed by {ctx.author.name}#{ctx.author.discriminator}")
    
    return role

def setup(bot):
    bot.add_cog(League(bot))
