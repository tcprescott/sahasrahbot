import os

import discord
from discord.ext import commands

from alttprbot.database import srlnick
from alttprbot import models

APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help="Register your Twitch name with SahasrahBot."
    )
    async def twitch(self, ctx, twitch):
        await srlnick.insert_twitch_name(ctx.author.id, twitch)

    @commands.command(
        help="Register your RaceTime.gg nick with SahasrahBot."
    )
    async def rtgg(self, ctx):
        await ctx.reply(f"Please visit <{APP_URL}/racetime/verification/initiate> to verify your RaceTime.gg ID!")

    @commands.command(
        help="List the nicknames registered with SahasrahBot."
    )
    async def getnick(self, ctx):
        nick = await srlnick.get_nickname(ctx.author.id)
        if nick:
            await ctx.reply(f"Your currently registered nickname for Twitch is `{nick[0]['twitch_name']}`")
        else:
            await ctx.reply("You currently do not have any nicknames registered with this bot.  Use the command `$twitch yournick` to do that!")

    @commands.command()
    @commands.is_owner()
    async def rtggblast(self, ctx, role_name: discord.Role):
        for member in role_name.members:
            result = await models.SRLNick.get_or_none(discord_user_id=member.id)
            if result is None or result.rtgg_id is None:
                try:
                    await member.send(
                        (f"Greetings {member.name}!  We have detected that you do not have a RaceTime.gg ID linked to SahasrahBot.\n"
                        f"Please visit <{APP_URL}/racetime/verification/initiate> to verify your RaceTime.gg ID!  We will need this info.\n\n"
                        "If you have any questions, please contact Synack.  Thank you!")
                    )
                    await ctx.send(f"Send DM to {member.name}#{member.discriminator}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await ctx.send(f"Failed to send DM to {member.name}#{member.discriminator}.\n\n{str(e)}")

    @commands.command()
    @commands.is_owner()
    async def rtggreport(self, ctx, role_name: discord.Role):
        msg = []
        for member in role_name.members:
            result = await models.SRLNick.get_or_none(discord_user_id=member.id)
            if result is None or result.rtgg_id is None:
                msg.append(f"{member.name}#{member.discriminator}")

        if msg:
            await ctx.reply("\n".join(msg))

def setup(bot):
    bot.add_cog(Nickname(bot))
