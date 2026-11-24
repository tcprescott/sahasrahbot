# Appropriated and modified from https://github.com/PaulMarisOUMary/Discord-Bot/blob/main/cogs/errors.py

import discord
from discord import app_commands
from discord.ext import commands


def _missing_permissions(error) -> str:
    return '` `'.join(error.missing_permissions)


def _command_error_message(ctx: commands.Context, error: commands.CommandError):
    """What to tell the user about a failed prefix or hybrid command, or None to say nothing more."""
    if isinstance(error, commands.MissingRequiredArgument):
        return f"Something is missing. `{ctx.clean_prefix}{ctx.command.name} <{'> <'.join(ctx.command.clean_params)}>`"
    if isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
        return f"Member `{str(error).split(' ')[1]}` not found ! Don't hesitate to ping the requested member."
    if isinstance(error, commands.CommandNotFound):
        return None
    if isinstance(error, commands.BotMissingPermissions):
        if "send_messages" in error.missing_permissions:
            return None
        return f"The bot require the following permissions: `{_missing_permissions(error)}`."
    if isinstance(error, commands.MissingPermissions):
        return f"Your account require the following permissions: `{_missing_permissions(error)}`."
    if isinstance(error, commands.CommandInvokeError):
        return str(error.original)
    if isinstance(error, commands.CommandOnCooldown):
        return f"Command is on cooldown, wait `{str(error).split(' ')[7]}` !"
    if isinstance(error, commands.MaxConcurrencyReached):
        return (f"Max concurrency reached. Maximum number of concurrent invokers allowed: `{error.number}`, "
                f"per `{error.per}`.")
    for error_type, message in _FIXED_COMMAND_ERROR_MESSAGES:
        if isinstance(error, error_type):
            return message
    if isinstance(error, _SELF_EXPLAINING_COMMAND_ERRORS):
        return str(error)
    return _UNHANDLED


# Returned by _command_error_message for errors the handler doesn't know.
_UNHANDLED = object()

_SELF_EXPLAINING_COMMAND_ERRORS = (
    commands.ConversionError, commands.BadArgument, commands.BadUnionArgument, commands.BadLiteralArgument,
    commands.ArgumentParsingError, commands.CheckAnyFailure, commands.MissingRole, commands.BotMissingRole,
    commands.MissingAnyRole, commands.BotMissingAnyRole,
)

_FIXED_COMMAND_ERROR_MESSAGES = (
    (commands.PrivateMessageOnly, "This command canno't be used in a guild, try in direct message."),
    (commands.NoPrivateMessage, "This is not working as excpected."),
    (commands.NotOwner, "You must own this bot to run this command."),
    (commands.NSFWChannelRequired, "This command require an NSFW channel."),
    (commands.DisabledCommand, "Sorry this command is disabled."),
)


def _invoke_error_message(original: Exception) -> str:
    """What to tell the user when an app command raised."""
    if isinstance(original, discord.errors.InteractionResponded):
        return str(original)
    if isinstance(original, discord.errors.Forbidden):
        return f"`{type(original).__name__}` : {original.text}"
    return f"`{type(original).__name__}` : {original}"


class Errors(commands.Cog, name="errors"):
    """Errors handler."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.tree.error(coro=self.__dispatch_to_app_command_handler)

        self.default_error_message = "There is an error."

    def trace_error(self, level: str, error: Exception):
        self.bot.logger.name = f"discord.{level}"
        self.bot.logger.error(msg=type(error).__name__, exc_info=error)

        raise error

    async def __dispatch_to_app_command_handler(self, interaction: discord.Interaction,
                                                error: discord.app_commands.AppCommandError):
        self.bot.dispatch("app_command_error", interaction, error)

    async def __respond_to_interaction(self, interaction: discord.Interaction) -> bool:
        try:
            await interaction.response.send_message(content=self.default_error_message, ephemeral=True)
            return True
        except discord.errors.InteractionResponded:
            return False

    @commands.Cog.listener("on_error")
    async def get_error(self, event, *args, **kwargs):
        """Error handler"""
        print(f"! Unexpected Internal Error: (event) {event}, (args) {args}, (kwargs) {kwargs}.")

    @commands.Cog.listener("on_command_error")
    async def get_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Command Error handler
        doc: https://discordpy.readthedocs.io/en/master/ext/commands/api.html#exception-hierarchy
        """

        riplink = discord.utils.get(ctx.bot.emojis, name='RIPLink')

        try:
            if ctx.interaction:  # HybridCommand Support
                await self.__respond_to_interaction(ctx.interaction)
                edit = ctx.interaction.edit_original_response
                if isinstance(error, commands.HybridCommandError):
                    error = error.original  # Access to the original error
            else:
                discord_message = await ctx.send(self.default_error_message)
                edit = discord_message.edit
        except Exception as e:
            self.trace_error("get_command_error", e)

        if isinstance(error, commands.HybridCommandError):
            await self.get_app_command_error(ctx.interaction, error)
            return

        content = _command_error_message(ctx, error)
        if content is _UNHANDLED:
            self.trace_error("get_command_error", error)
        if content is not None:
            await edit(content=f"{riplink} {content}")

    @commands.Cog.listener("on_app_command_error")
    async def get_app_command_error(self, interaction: discord.Interaction,
                                    error: discord.app_commands.AppCommandError):
        """App command Error Handler
        doc: https://discordpy.readthedocs.io/en/master/interactions/api.html#exception-hierarchy
        """

        riplink = discord.utils.get(self.bot.emojis, name='RIPLink')

        try:
            await self.__respond_to_interaction(interaction)
            edit = interaction.edit_original_response
        except Exception as e:
            self.trace_error("get_app_command_error", e)

        if isinstance(error, app_commands.CommandInvokeError):
            await edit(content=f"{riplink} {_invoke_error_message(error.original)}")
            self.bot.logger.error("Error during interaction", exc_info=error)
        elif isinstance(error, app_commands.errors.CommandOnCooldown):
            await edit(content=f"{riplink} Command is on cooldown, wait `{str(error).split(' ')[7]}` !")
        elif isinstance(error, app_commands.CheckFailure):
            await edit(content=f"{riplink} `{type(error).__name__}` : {error}")
        elif isinstance(error, app_commands.CommandNotFound):
            await edit(
                content=f"{riplink} Command was not found.. Seems to be a discord bug, probably due to desynchronization.\nTry again in a little bit, and if this still happens after an hour contact Synack for help.")
            raise error
        else:
            # For example app_commands.TransformerError, CommandLimitReached,
            # CommandAlreadyRegistered and CommandSignatureMismatch.
            self.trace_error("get_app_command_error", error)

    @commands.Cog.listener("on_view_error")
    async def get_view_error(self, interaction: discord.Interaction, error: Exception, item: any):
        """View Error Handler"""
        try:
            raise error
        except discord.errors.Forbidden:
            pass
        except Exception as e:
            self.trace_error("get_view_error", e)

    @commands.Cog.listener("on_modal_error")
    async def get_modal_error(self, interaction: discord.Interaction, error: Exception):
        """Modal Error Handler"""
        try:
            raise error
        except discord.errors.Forbidden:
            pass
        except Exception as e:
            self.trace_error("get_modal_error", e)


async def setup(bot: commands.Bot):
    await bot.add_cog(Errors(bot))
