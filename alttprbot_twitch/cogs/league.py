from twitchio.ext import commands
from alttprbot.database import twitch_command_text

@commands.core.cog()
class League():
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def mode(self, ctx):
        result = await twitch_command_text.get_command_text(
            channel=ctx.channel.name.lower(),
            command="mode"
        )
        if result is not None:
            await ctx.send(result['content'])

def setup(bot):
    bot.add_cog(League(bot))