import discord
from discord.commands import permissions, ApplicationContext, Option
from discord.ext import commands


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    guildconfig = discord.commands.SlashCommandGroup(
        "guildconfig",
        "Miscellaneous guild configuration commands for the bot's owner.",
        # permissions=[
        #     permissions.CommandPermission(
        #         "owner", 2, True
        #     )
        # ]
    )

    @guildconfig.command()
    async def set(self, ctx: ApplicationContext, parameter: Option(str), value: Option(str)):
        """
        Set a guild configuration parameter.
        """
        ctx.guild.config.set(parameter, value)
        await ctx.respond(f"Set {parameter} to {value}", ephemeral=True)

    @guildconfig.command()
    async def get(self, ctx: ApplicationContext):
        """
        Get a guild configuration parameter.
        """
        await ctx.respond(ctx.guild.config.dump(), ephemeral=True)

    @guildconfig.command()
    async def delete(self, ctx: ApplicationContext, parameter: Option(str)):
        """
        Delete a guild configuration parameter.
        """
        ctx.guild.config.delete(parameter)
        await ctx.respond(f"Deleted {parameter}", ephemeral=True)

    # @guildconfig.command()
    # async def reloadall(self, ctx: ApplicationContext):
    #     for guild in self.bot.guilds():
    #         guild.config = GuildConfig(guild.id)
    #     await ctx.respond("Reloaded all guild configs", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Config(bot))
