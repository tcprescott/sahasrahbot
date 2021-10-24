import dateutil.parser
import discord
from alttprbot.util import speedgaming
from discord.ext import commands


class SgDaily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief="Retrieves the next ALTTPR SG daily race.",
        help="Retrieves the next ALTTPR SG daily race.",
    )
    @commands.cooldown(rate=2, per=900, type=commands.BucketType.channel)
    async def sgdaily(self, ctx, get_next=1):
        sg_schedule = await speedgaming.get_upcoming_episodes_by_event('alttprdaily', hours_past=0, hours_future=192)
        if len(sg_schedule) == 0:
            await ctx.reply("There are no currently SpeedGaming ALTTPR Daily Races scheduled within the next 8 days.")
            return

        if get_next == 1:
            embed = discord.Embed(
                title=sg_schedule[0]['event']['name'],
                description=f"**Mode:** {'*TBD*' if sg_schedule[0]['match1']['title'] == '' else sg_schedule[0]['match1']['title']}\n[Full Schedule](http://speedgaming.org/alttprdaily)"
            )
        else:
            embed = discord.Embed(
                title="ALTTP Randomizer SG Daily Schedule",
                description="[Full Schedule](http://speedgaming.org/alttprdaily)"
            )

        for episode in sg_schedule[0:get_next]:
            when = dateutil.parser.parse(episode['when'])
            if get_next == 1:
                embed.add_field(
                    name='Time', value=f"{discord.utils.format_dt(when, 'f')} ({discord.utils.format_dt(when, 'R')})", inline=False)
                broadcast_channels = [a['slug'] for a in episode['channels'] if not " " in a['name']]
                if broadcast_channels:
                    embed.add_field(name="Twitch Channels", value=', '.join(
                        [f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
            else:
                embed.add_field(
                    name='TBD' if episode['match1']['title'] == '' else episode['match1']['title'],
                    value=discord.utils.format_dt(when, 'f'),
                    inline=False
                )
        embed.set_footer()

        embed.set_thumbnail(
            url='https://pbs.twimg.com/profile_images/1185422684190105600/3jiXIf5Y_400x400.jpg')
        await ctx.reply(embed=embed)


def setup(bot):
    bot.add_cog(SgDaily(bot))
