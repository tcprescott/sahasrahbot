from discord.ext import commands
from alttprbot.database import config
from alttprbot.exceptions import SahasrahBotException
import aiohttp
from config import Config as c  # pylint: disable=no-name-in-module

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

        for division in roster['divisions']:
            division_role = await find_or_create_role(ctx, f"Division - {division['name']}")
            player_role = await find_or_create_role(
                ctx,
                "Racer" if division['invitational'] else "Open Racer"
            )
            for team in division['teams']:
                team_role = await find_or_create_role(ctx, team['name'])

                for pendant in ['courage', 'wisdom', 'power']:
                    if c.DEBUG:
                        print(f"would have added \"{team[pendant]['discord']}\" to role \"{division_role.name}\"")
                        print(f"would have added \"{team[pendant]['discord']}\" to role \"{player_role.name}\"")
                        print(f"would have added \"{team[pendant]['discord']}\" to role \"{team_role.name}\"")
                        print(f"would have added \"{team[pendant]['discord']}\" to role \"{pendant_roles[pendant].name}\"")
                    else:
                        try:
                            team_member = await commands.MemberConverter().convert(ctx, team[pendant]['discord'])
                        except commands.MemberNotFound:
                            await ctx.send(f"Could not resolve user {team[pendant]['discord']}, skipping...")
                            continue
                        await team_member.add_roles(division_role, player_role, team_role, pendant_roles[pendant])
                    
            # if not mode == "dry":
            #     await member_obj.add_roles(role_obj)

async def find_or_create_role(ctx, role_name):
    try:
        role = await commands.RoleConverter().convert(ctx, role_name)
    except commands.RoleNotFound:
        role = await ctx.guild.create_role(name=role_name)
    
    return role

def setup(bot):
    bot.add_cog(League(bot))
