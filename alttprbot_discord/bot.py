import importlib
import logging

import discord
from discord.ext import commands
from discord_sentry_reporting import use_sentry

import config
# No privileged intents: member lookups go through alttprbot/util/discord_members.py.
intents = discord.Intents.default()

discordbot = commands.Bot(
    command_prefix=commands.when_mentioned_or("$"),
    allowed_mentions=discord.AllowedMentions(
        everyone=False,
        users=True,
        roles=False
    ),
    intents=intents,
    chunk_guilds_at_startup=False,
)

discordbot.logger = logging.getLogger('discord')
discordbot.logger.setLevel(logging.INFO)

if config.SENTRY_URL:
    use_sentry(discordbot, dsn=config.SENTRY_URL)


async def load_extensions():
    await discordbot.load_extension("alttprbot_discord.cogs.errors")
    await discordbot.load_extension("alttprbot_discord.cogs.daily")
    await discordbot.load_extension("alttprbot_discord.cogs.discord_servers")
    await discordbot.load_extension("alttprbot_discord.cogs.misc")
    await discordbot.load_extension("alttprbot_discord.cogs.role")
    await discordbot.load_extension("alttprbot_discord.cogs.sgdailies")
    await discordbot.load_extension("alttprbot_discord.cogs.voicerole")
    await discordbot.load_extension("alttprbot_discord.cogs.smmulti")
    await discordbot.load_extension("alttprbot_discord.cogs.generator")
    await discordbot.load_extension("alttprbot_discord.cogs.inquiry")
    await discordbot.load_extension("alttprbot_discord.cogs.rankedchoice")
    await discordbot.load_extension("alttprbot_discord.cogs.doorsmw")
    await discordbot.load_extension("alttprbot_discord.cogs.racer_verification")

    await discordbot.load_extension('jishaku')

    # if importlib.util.find_spec('sahasrahbot_private'):
    #     await discordbot.load_extension('sahasrahbot_private.stupid_memes')


# @discordbot.event
# async def on_command_error(ctx, error):
#     riplink = discord.utils.get(ctx.bot.emojis, name='RIPLink')
#     await ctx.message.remove_reaction('⌚', ctx.bot.user)
#     logging.info(error)
#     if isinstance(error, commands.CheckFailure):
#         pass
#     elif isinstance(error, commands.errors.MissingPermissions):
#         await ctx.message.add_reaction('🚫')
#     elif isinstance(error, commands.CommandNotFound):
#         pass
#     elif isinstance(error, commands.UserInputError):
#         if riplink is None:
#             riplink = '👎'
#         await ctx.reply(error)
#     else:
#         if riplink is None:
#             riplink = '👎'
#         error_to_display = error.original if hasattr(
#             error, 'original') else error

#         await ctx.message.add_reaction(riplink)

#         errorstr = repr(error_to_display)
#         if len(errorstr) < 1990:
#             await ctx.reply(f"```{errorstr}```")
#         else:
#             await ctx.reply(
#                 content="An error occured, please see attachment for the full message.",
#                 file=discord.File(io.StringIO(error_to_display), filename="error.txt")
#             )
#         with push_scope() as scope:
#             scope.set_tag("guild", ctx.guild.id if ctx.guild else "")
#             scope.set_tag("channel", ctx.channel.id if ctx.channel else "")
#             scope.set_tag("user", f"{ctx.author.name}#{ctx.author.discriminator}" if ctx.author else "")
#             raise error_to_display


@discordbot.event
async def on_command(ctx):
    await ctx.message.add_reaction('⌚')


@discordbot.event
async def on_command_completion(ctx):
    await ctx.message.add_reaction('✅')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)


@discordbot.event
async def on_ready():
    if config.DEBUG:
        discordbot.tree.copy_global_to(guild=discord.Object(id=508335685044928540))  # hard code the discord server id for now
        discordbot.tree.clear_commands(guild=None)
    
    await discordbot.tree.sync()

    for guild in discordbot.guilds:
        cmds = discordbot.tree.get_commands(guild=guild)
        if cmds:
            discordbot.logger.info("Loaded {} commands for {}".format(len(cmds), guild.name))
            await discordbot.tree.sync(guild=guild)


async def start_bot():
    await load_extensions()
    await discordbot.start(config.DISCORD_TOKEN)
