import random

from discord.ext import commands

from alttprbot import models
from alttprbot.alttprgen.preset import generate_preset, fetch_preset
from config import Config as c


def restrict_sgl_channels():
    async def predicate(ctx):
        if ctx.channel is None:
            return False
        if ctx.channel.id in [508335685044928548, 772351829022474260]:
            return True

        return False
    return commands.check(predicate)

class SpeedGamingLive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @restrict_sgl_channels()
    async def sglqual(self, ctx):
        triforce_text = await models.TriforceTexts.filter(broadcasted=False, pool_name='sglqual').first()

        if triforce_text is None:
            triforce_texts = await models.TriforceTexts.filter(pool_name='sglqual')
            triforce_text = random.choice(triforce_texts)

        text = triforce_text.text.encode("utf-8").decode("unicode_escape")

        preset_dict = await fetch_preset('sglive')
        preset_dict['settings']['texts'] = {}
        preset_dict['settings']['texts']['end_triforce'] = "{NOBORDER}\n{SPEED6}\n" + text + "\n{PAUSE9}"
        seed = await generate_preset(preset_dict)

        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.reply(embed=embed)

        triforce_text.broadcasted = True
        await triforce_text.save()

def setup(bot):
    bot.add_cog(SpeedGamingLive(bot))
