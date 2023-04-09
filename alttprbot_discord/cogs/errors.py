# Appropriated and modified from https://github.com/PaulMarisOUMary/Discord-Bot/blob/main/cogs/errors.py

import discord

from discord.ext import commands
from discord import app_commands


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

    async def __dispatch_to_app_command_handler(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
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

        edit = None

        try:
            if ctx.interaction:  # HybridCommand Support
                await self.__respond_to_interaction(ctx.interaction)
                edit = ctx.interaction.edit_original_message
                if isinstance(error, commands.HybridCommandError):
                    error = error.original  # Access to the original error
            else:
                discord_message = await ctx.send(self.default_error_message)
                edit = discord_message.edit

            raise error

        # ConversionError
        except commands.ConversionError as d_error:
            if edit is not None:
                await edit(content=f"{riplink} {d_error}") # pylint: disable=no-member
        # UserInputError
        except commands.MissingRequiredArgument:
            if edit is not None:
                await edit(content=f"{riplink} Something is missing. `{ctx.clean_prefix}{ctx.command.name} <{'> <'.join(ctx.command.clean_params)}>`")
        # UserInputError -> BadArgument
        except (commands.MemberNotFound, commands.UserNotFound):
            if edit is not None:
                await edit(content=f"{riplink} Member `{str(d_error).split(' ')[1]}` not found ! Don't hesitate to ping the requested member.")
        # UserInputError -> BadUnionArgument | BadLiteralArgument | ArgumentParsingError
        except (commands.BadArgument, commands.BadUnionArgument, commands.BadLiteralArgument, commands.ArgumentParsingError) as d_error:
            if edit is not None:
                await edit(content=f"{riplink} {d_error}")
        # CommandNotFound
        except commands.CommandNotFound as d_error:
            # await edit(content=f"{riplink} Command `{str(d_error).split(' ')[1]}` not found !")
            pass  # Ignore this error
        # CheckFailure
        except commands.PrivateMessageOnly:
            if edit is not None:
                await edit(content=f"{riplink} This command canno't be used in a guild, try in direct message.")
        except commands.NoPrivateMessage:
            if edit is not None:
                await edit(content=f"{riplink} This is not working as excpected.")
        except commands.NotOwner:
            if edit is not None:
                await edit(content=f"{riplink} You must own this bot to run this command.")
        except commands.MissingPermissions as d_error:
            if edit is not None:
                await edit(content=f"{riplink} Your account require the following permissions: `{'` `'.join(d_error.missing_permissions)}`.")
        except commands.BotMissingPermissions as d_error:
            if edit is not None:
                if not "send_messages" in d_error.missing_permissions:
                    await edit(content=f"{riplink} The bot require the following permissions: `{'` `'.join(d_error.missing_permissions)}`.")
        except (commands.CheckAnyFailure, commands.MissingRole, commands.BotMissingRole, commands.MissingAnyRole, commands.BotMissingAnyRole) as d_error:
            if edit is not None:
                await edit(content=f"{riplink} {d_error}")
        except commands.NSFWChannelRequired:
            if edit is not None:
                await edit(content=f"{riplink} This command require an NSFW channel.")
        # DisabledCommand
        except commands.DisabledCommand:
            if edit is not None:
                await edit(content=f"{riplink} Sorry this command is disabled.")
        # CommandInvokeError
        except commands.CommandInvokeError as d_error:
            if edit is not None:
                await edit(content=f"{riplink} {d_error.original}")
        # CommandOnCooldown
        except commands.CommandOnCooldown as d_error:
            if edit is not None:
                await edit(content=f"{riplink} Command is on cooldown, wait `{str(d_error).split(' ')[7]}` !")
        # MaxConcurrencyReached
        except commands.MaxConcurrencyReached as d_error:
            if edit is not None:
                 await edit(content=f"{riplink} Max concurrency reached. Maximum number of concurrent invokers allowed: `{d_error.number}`, per `{d_error.per}`.")
        # HybridCommandError
        except commands.HybridCommandError as d_error:
            await self.get_app_command_error(ctx.interaction, error)
        except Exception as e:
            self.trace_error("get_command_error", e)

    @commands.Cog.listener("on_app_command_error")
    async def get_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """App command Error Handler
        doc: https://discordpy.readthedocs.io/en/master/interactions/api.html#exception-hierarchy
        """

        riplink = discord.utils.get(self.bot.emojis, name='RIPLink')
        edit = None

        try:
            await self.__respond_to_interaction(interaction)
            edit = interaction.edit_original_response

            raise error
        except app_commands.CommandInvokeError as d_error:
            if isinstance(d_error.original, discord.errors.InteractionResponded):
                if edit is not None:
                    await edit(content=f"{riplink} {d_error.original}")
                self.bot.logger.exception("Error during interaction")
            elif isinstance(d_error.original, discord.errors.Forbidden):
                if edit is not None:
                    await edit(content=f"{riplink} `{type(d_error.original).__name__}` : {d_error.original.text}")
                self.bot.logger.exception("Error during interaction")
            else:
                if edit is not None:
                    await edit(content=f"{riplink} `{type(d_error.original).__name__}` : {d_error.original}")
                self.bot.logger.exception("Error during interaction")
        except app_commands.CheckFailure as d_error:
            if isinstance(d_error, app_commands.errors.CommandOnCooldown):
                if edit is not None:
                    await edit(content=f"{riplink} Command is on cooldown, wait `{str(d_error).split(' ')[7]}` !")
            else:
                if edit is not None:
                    await edit(content=f"{riplink} `{type(d_error).__name__}` : {d_error}")
        except app_commands.CommandNotFound as d_error:
            if edit is not None:
                await edit(content=f"{riplink} Command was not found.. Seems to be a discord bug, probably due to desynchronization.\nTry again in a little bit, and if this still happens after an hour contact Synack for help.")
            raise d_error
        except Exception as e:
            # Caught here:
            # app_commands.TransformerError
            # app_commands.CommandLimitReached
            # app_commands.CommandAlreadyRegistered
            # app_commands.CommandSignatureMismatch

            self.trace_error("get_app_command_error", e)

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
