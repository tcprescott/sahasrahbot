import math

from alttprbot.database import config, gtbk
from alttprbot_srl.bot import srlbot
from discord.ext import commands

from ..util import embed_formatter


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if await ctx.bot.is_owner(ctx.author):
            return True

        return False

    @commands.command(
        help='Set a parameter.'
    )
    async def configset(self, ctx, parameter, value):
        guildid = ctx.guild.id if ctx.guild else 0
        await config.set_parameter(guildid, parameter, value)

    @commands.command(
        help='Get a parameter.'
    )
    async def configget(self, ctx):
        guildid = ctx.guild.id if ctx.guild else 0
        result = await config.get_parameters_by_guild(guildid)
        await ctx.reply(embed=embed_formatter.config(ctx, result))

    @commands.command(
        help='Delete a parameter.'
    )
    async def configdelete(self, ctx, parameter):
        guildid = ctx.guild.id if ctx.guild else 0
        await config.delete_parameter(guildid, parameter)

    @commands.command(
        brief='Clear the configuration cache.',
        help='Clear the configuration cache.  Useful if database was manually updated.'
    )
    async def configcache(self, ctx):
        await config.CACHE.clear()

    @commands.command()
    async def srlmsg(self, ctx, channel, message):
        await srlbot.message(channel, message)

    @commands.command()
    async def srljoin(self, ctx, channel):
        await srlbot.join(channel)

    @commands.command()
    async def srlpart(self, ctx, channel):
        await srlbot.part(channel)

    @commands.command()
    async def srlnotice(self, ctx, channel, message):
        await srlbot.notice(channel, message)

    @commands.command()
    async def srljoinall(self, ctx):
        await srlbot.join_active_races(['alttphacks', 'alttpsm', 'supermetroidhacks'])

    @commands.command()
    async def gtbkrecalc(self, ctx, game_id: int, key: int, dry: bool = True):
        game = await gtbk.get_game(game_id)
        if not game:
            raise gtbk.GtbkGuessingGameException(
                "Game does not exist.")

        points = await calculate_score(game_id)

        winner = await get_winner(key, game_id)
        runnerups = await get_runnerups(key, game_id, winner)

        if dry:
            await ctx.reply("would have cleared scores")
        else:
            await gtbk.clear_scores(game_id)

        if dry:
            await ctx.reply(f"would have given {winner['twitch_user']} {points} points")
        else:
            await gtbk.update_score(guess_id=winner['guess_id'], score=points)

        for runnerup in runnerups:
            if dry:
                await ctx.reply(f"would have given {runnerup['twitch_user']} 5 points")
            else:
                await gtbk.update_score(guess_id=runnerup['guess_id'], score=5)


async def calculate_score(game_id):
    guessdict = await gtbk.get_guesses(game_id)
    cnt = len(guessdict)
    if cnt <= 25:
        score = math.ceil((cnt - 1)/2) + 5
    else:
        score = math.ceil(17 + ((cnt-26) / 25) * 10)

    return score


async def get_winner(key: int, game_id):
    guessdict = await gtbk.get_guesses(game_id)
    value = min(guessdict, key=lambda kv: abs(kv['guess'] - key))
    return value


async def get_runnerups(key: int, game_id, winner):
    guessdict = await gtbk.get_guesses(game_id)
    runners_up = []
    for guess in guessdict:
        if guess['guess'] == key and not guess['twitch_user'] == winner['twitch_user']:
            runners_up.append(guess)
    return runners_up


def setup(bot):
    bot.add_cog(Admin(bot))
