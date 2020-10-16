from discord.ext import commands
from alttprbot_racetime.tools import create_race
from alttprbot_racetime.bot import racetime_sgl
from alttprbot.database import config


class SpeedGamingLive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if ctx.guild is None:
            return False

        if await config.get(ctx.guild.id, 'SpeedGamingLiveEnabled') == 'true':
            return True
        else:
            return False

    @commands.command(
        help="Generate a SGL race room on racetime."
    )
    @commands.is_owner()
    async def sgltest(self, ctx):
        room_name = await create_race(
            game='sgl',
            config={
                'goal': 1450,
                'custom_goal': '',
                'invitational': 'on',
                'unlisted': 'on',
                'info': 'bot testing',
                'start_delay': 15,
                'time_limit': 24,
                'streaming_required': 'on',
                'allow_comments': 'on',
                'allow_midrace_chat': 'on',
                'allow_non_entrant_chat': 'off',
                'chat_message_delay': 0})

        await racetime_sgl.create_handler_by_room_name(room_name)
        await ctx.send(f'https://racetime.gg{room_name}')


def setup(bot):
    bot.add_cog(SpeedGamingLive(bot))
