import os

import discord
from discord.commands import permissions, ApplicationContext, Option, SlashCommandGroup
from discord.ext import commands
from racetime_bot import Bot

from alttprbot import models


async def role_name_autocomplete(ctx):
    return [r.name for r in ctx.interaction.guild.roles if r.name.startswith(ctx.value)][:25]

APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')


class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    # @commands.command(
    #     help="Register your Twitch name with SahasrahBot."
    # )
    # async def twitch(self, ctx, twitch):
    #     await srlnick.insert_twitch_name(ctx.author.id, twitch)

    # @commands.command(
    #     help="Register your RaceTime.gg nick with SahasrahBot."
    # )
    # async def rtgg(self, ctx):
    #     await ctx.reply(f"Please visit <{APP_URL}/racetime/verification/initiate> to verify your RaceTime.gg ID!")

    # @commands.command(
    #     help="List the nicknames registered with SahasrahBot."
    # )
    # async def getnick(self, ctx):
    #     nick = await srlnick.get_nickname(ctx.author.id)
    #     if nick:
    #         await ctx.reply(f"Your currently registered nickname for Twitch is `{nick[0]['twitch_name']}`")
    #     else:
    #         await ctx.reply("You currently do not have any nicknames registered with this bot.  Use the command `$twitch yournick` to do that!")

    rtggadmin = SlashCommandGroup(
        "rtgg",
        "Miscellaneous administrative commands for RaceTime.gg",
    )

    @rtggadmin.command()
    async def blast(self, ctx: ApplicationContext, role_name: Option(str, "Choose a role to blast", required=True, autocomplete=role_name_autocomplete)):
        """
        Used by Synack to blast requests to link your RaceTime.gg account to this bot.
        """
        if not await self.bot.is_owner(ctx.author):
            await ctx.reply("Only the bot owner can use this command.")
            return

        role: discord.Role = discord.utils.get(ctx.guild._roles.values(), name=role_name)
        await ctx.defer()
        msg = []
        for member in role.members:
            result = await models.SRLNick.get_or_none(discord_user_id=member.id)
            if result is None or result.rtgg_id is None:
                try:
                    await member.send(
                        (f"Greetings {member.name}!  We have detected that you do not have a RaceTime.gg ID linked to SahasrahBot.\n"
                         f"Please visit <{APP_URL}/racetime/verification/initiate> to verify your RaceTime.gg ID!  We will need this info.\n\n"
                         "If you have any questions, please contact Synack.  Thank you!")
                    )
                    msg.append(f"Send DM to {member.name}#{member.discriminator}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    msg.append(f"Failed to send DM to {member.name}#{member.discriminator}.\n\n{str(e)}")

        if msg:
            await ctx.respond("\n".join(msg))
        else:
            await ctx.respond("No messages sent.")

    @rtggadmin.command()
    async def report(self, ctx: ApplicationContext, role_name: Option(str, "Choose a role to report", required=True, autocomplete=role_name_autocomplete)):
        """
        Used by Synack to report users who have not linked their racetime account to SahasrahBot.
        """
        if not await self.bot.is_owner(ctx.author):
            await ctx.reply("Only the bot owner can use this command.")
            return

        await ctx.defer()
        role: discord.Role = discord.utils.get(ctx.guild._roles.values(), name=role_name)
        msg = []
        for member in role.members:
            result = await models.SRLNick.get_or_none(discord_user_id=member.id)
            if result is None or result.rtgg_id is None:
                msg.append(f"{member.name}#{member.discriminator}")

        if msg:
            await ctx.respond("\n".join(msg))

        else:
            await ctx.respond("Everyone in this role is registered with the bot.")


def setup(bot):
    bot.add_cog(Nickname(bot))
