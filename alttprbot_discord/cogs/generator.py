from discord.ext import commands
from discord.commands import ApplicationContext, Option
from alttprbot.alttprgen import generator
from alttprbot.exceptions import SahasrahBotException
from alttprbot.alttprgen.spoilers import generate_spoiler_game
from alttprbot.alttprgen import smvaria
from alttprbot.alttprgen.randomizer import smdash


class Generator(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.slash_command()
    async def alttpr(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True),
        race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no"),
        hints: Option(str, description="Enable hints? (default no)", choices=["yes", "no"], required=False, default="no"),
        allow_quickswap: Option(str, description="Allow quickswap? (default yes)", choices=["yes", "no"], required=False, default="yes")
    ):
        """
        Generates an ALTTP Randomizer game on https://alttpr.com
        """
        await ctx.defer()
        seed = await generator.ALTTPRPreset(preset).generate(
            hints=hints == "yes",
            spoilers="off" if race == "yes" else "on",
            tournament=race == "yes",
            allow_quickswap=allow_quickswap == "yes"
        )
        if not seed:
            raise SahasrahBotException('Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)

        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def alttprspoiler(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True),
    ):
        """
        Generates an ALTTP Randomizer Spoiler Race on https://alttpr.com
        """
        await ctx.defer()
        spoiler = await generate_spoiler_game(preset)

        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Spoiler Log URL", value=spoiler.spoiler_log_url, inline=False)

        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def alttprmystery(
        self,
        ctx: ApplicationContext,
        weightset: Option(str, description="The weightset you want to use.", required=True),
        race: Option(str, description="Is this a race? (choosing no never masks settings) (default yes)", choices=["yes", "no"], required=False, default="yes"),
        mask_settings: Option(str, description="Mask settings? (default yes)", choices=["yes", "no"], required=False, default="yes"),
    ):
        """
        Generates an ALTTP Randomizer Mystery game on https://alttpr.com
        """
        await ctx.defer()
        mystery = await generator.ALTTPRMystery(weightset).generate(
            spoilers="mystery" if mask_settings else "off",
            tournament=race == "yes"
        )

        embed = await mystery.seed.embed(emojis=ctx.bot.emojis, name="Mystery Game")

        if mystery.custom_instructions:
            embed.insert_field_at(0, name="Custom Instructions", value=mystery.custom_instructions, inline=False)

        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def sm(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True),
        race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no"),
    ):
        """
        Generates an Super Metroid Randomizer game on https://sm.samus.link
        """
        await ctx.defer()
        seed = await generator.SMPreset(preset).generate(tournament=race == "yes")
        embed = await seed.embed()
        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def smz3(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True),
        race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no")
    ):
        """
        Generates an ALTTP Super Metroid Combo Randomizer game on https://samus.link
        """
        await ctx.defer()
        seed = await generator.SMZ3Preset(preset).generate(tournament=race == "yes")
        embed = await seed.embed()
        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def smvaria(
        self,
        ctx: ApplicationContext,
        skills: Option(str, description="The skills preset you want to use.", required=True),
        settings: Option(str, description="The settings preset you want generate.", required=True),
        race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no")
    ):
        """
        Generates an Super Metroid Varia Randomizer game on https://varia.run
        """
        await ctx.defer()
        seed = await smvaria.generate_preset(
            settings=settings,
            skills=skills,
            race=race == "yes"
        )
        await ctx.respond(embed=seed.embed())

    @commands.slash_command()
    async def smdash(
        self,
        ctx: ApplicationContext,
        mode: Option(str, description="The mode you want to generate.", choices=['mm', 'full', 'sgl20', 'vanilla'], required=True),
        race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no")
    ):
        """
        Generates an Super Metroid Varia Randomizer game on https://varia.run
        """
        await ctx.defer()
        url = await smdash.create_smdash(mode=mode, encrypt=race == "yes")
        await ctx.respond(url)

    @ commands.slash_command()
    async def ctjets(self, ctx: ApplicationContext, preset: Option(str, description="The preset you want to generate.", required=True)):
        """
        Generates a Chrono Trigger: Jets of Time randomizer game on http://ctjot.com
        """
        seed_uri = await generator.CTJetsPreset(preset).generate()
        await ctx.respond(seed_uri)


def setup(bot):
    bot.add_cog(Generator(bot))
