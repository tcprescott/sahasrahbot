import discord
from alttprbot import models
from alttprbot.alttprgen import generator, smvaria
from alttprbot.alttprgen.randomizer import smdash, z2r
from alttprbot.alttprgen.spoilers import generate_spoiler_game
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord
from alttprbot_discord.util.alttprdoors_discord import AlttprDoorDiscord
from discord.commands import ApplicationContext, Option
from discord.ext import commands
from pyz3r.ext.priestmode import create_priestmode


async def autocomplete_alttpr(ctx):
    return await generator.ALTTPRPreset().search(ctx.value)


async def autocomplete_alttprmystery(ctx):
    return await generator.ALTTPRMystery().search(ctx.value)


async def autocomplete_sm(ctx):
    return await generator.SMPreset().search(ctx.value)


async def autocomplete_smz3(ctx):
    return await generator.SMZ3Preset().search(ctx.value)


async def autocomplete_ctjets(ctx):
    return await generator.CTJetsPreset().search(ctx.value)


async def autocomplete_smvaria_skills(ctx):
    skills = ['SMRAT2021', 'Season_Races', 'Torneio_SGPT2', 'casual', 'expert', 'master', 'newbie', 'regular', 'samus', 'solution', 'veteran']
    return sorted([a for a in skills if a.startswith(ctx.value)][:25])


async def autocomplete_smvaria_settings(ctx):
    settings = [
        'Chozo_Speedrun',
        'SGLive2021',
        'SMRAT2021',
        'Season_Races',
        'Torneio_SGPT2',
        'VARIA_Weekly',
        'all_random',
        'default',
        'doors_long',
        'doors_short',
        'free',
        'hardway2hell',
        'haste',
        'highway2hell',
        'hud',
        'hud_hard',
        'hud_start',
        'minimizer',
        'minimizer_hardcore',
        'minimizer_maximizer',
        'quite_random',
        'scavenger_hard',
        'scavenger_random',
        'scavenger_speedrun',
        'scavenger_vanilla_but_not',
        'stupid_hard',
        'surprise',
        'vanilla',
        'way_of_chozo',
        'where_am_i',
        'where_is_morph',
    ]
    return sorted([a for a in settings if a.startswith(ctx.value)][:25])

class ALTTPRPresetView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, error: Exception, item, interaction) -> None:
        raise error

    @discord.ui.button(label="Generate Again", style=discord.ButtonStyle.blurple, custom_id="sahabot:generator:regen", row=1)
    async def regenerate(self, button: discord.ui.Button, interaction: discord.Interaction):
        respmsg = await interaction.response.send_message("Generating, please wait...")
        permalink = get_embed_field("Permalink", interaction.message.embeds[0])
        audit_game = await models.AuditGeneratedGames.get(permalink=permalink)

        if audit_game.doors:
            seed = await AlttprDoorDiscord.create(
                settings=audit_game.settings,
                spoilers=True
            )
        else:
            seed = await ALTTPRDiscord.generate(
                settings=audit_game.settings,
                endpoint='/api/customizer' if audit_game.customizer else '/api/randomizer'
            )

        await models.AuditGeneratedGames.create(
            randomizer='alttpr',
            hash_id=seed.hash,
            permalink=seed.url,
            settings=audit_game.settings,
            gentype='preset',
            genoption=audit_game.genoption,
            customizer=1 if audit_game.customizer else 0,
            doors=audit_game.doors
        )

        embed = await seed.embed(emojis=discordbot.emojis)
        embed.insert_field_at(0, name="Preset", value=audit_game.genoption, inline=False)
        await respmsg.edit_original_message(content=None, embed=embed, view=ALTTPRPresetView())

class Generator(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(ALTTPRPresetView())
            self.persistent_views_added = True

    alttpr = discord.commands.SlashCommandGroup("alttpr", "Generate a game for the ALTTP Randomizer")

    @alttpr.command()
    async def preset(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True, autocomplete=autocomplete_alttpr),
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
        embed.insert_field_at(0, name="Preset", value=preset, inline=False)

        await ctx.respond(embed=embed, view=ALTTPRPresetView())

    # @alttpr.command()
    # async def festive(
    #     self,
    #     ctx: ApplicationContext,
    #     preset: Option(str, description="The preset you want generate.", required=True, autocomplete=autocomplete_alttpr),
    #     race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no"),
    #     hints: Option(str, description="Enable hints? (default no)", choices=["yes", "no"], required=False, default="no"),
    #     allow_quickswap: Option(str, description="Allow quickswap? (default yes)", choices=["yes", "no"], required=False, default="yes")
    # ):
    #     """
    #     Generates an Festive™ ALTTP Randomizer game on https://alttpr.com/festive
    #     """
    #     await ctx.defer()
    #     seed = await generator.ALTTPRPreset(preset).generate(
    #         hints=hints == "yes",
    #         spoilers="off" if race == "yes" else "on",
    #         tournament=race == "yes",
    #         allow_quickswap=allow_quickswap == "yes",
    #         endpoint_prefix="/festive"
    #     )
    #     if not seed:
    #         raise SahasrahBotException('Could not generate game.  Maybe preset does not exist?')
    #     embed = await seed.embed(emojis=self.bot.emojis)

    #     await ctx.respond(embed=embed)

    @alttpr.command()
    async def spoiler(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True, autocomplete=autocomplete_alttpr),
        festive: Option(str, description="Use the festive randomizer? (default no)", choices=["yes", "no"], required=False, default="no"),
    ):
        """
        Generates an ALTTP Randomizer Spoiler Race on https://alttpr.com
        """
        await ctx.defer()
        spoiler = await generate_spoiler_game(preset, festive=festive == "yes")

        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Preset", value=preset, inline=False)
        embed.insert_field_at(0, name="Spoiler Log URL", value=spoiler.spoiler_log_url, inline=False)

        await ctx.respond(embed=embed)

    @alttpr.command()
    async def mystery(
        self,
        ctx: ApplicationContext,
        weightset: Option(str, description="The weightset you want to use.", required=True, autocomplete=autocomplete_alttprmystery),
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
        embed.insert_field_at(0, name="Weightset", value=weightset, inline=False)

        await ctx.respond(embed=embed)

    @alttpr.command()
    async def kisspriest(
        self,
        ctx: ApplicationContext,
        count: Option(int, description="Number of seeds to generate.  Default is 10.", required=False, default=10, min_value=1, max_value=10)
    ):
        """
        Create a series a \"Kiss Priest\" games.  This was created by hycutype.
        """
        await ctx.defer()

        seeds = await create_priestmode(count=count, genclass=ALTTPRDiscord)
        embed = discord.Embed(
            title='Kiss Priest Games',
            color=discord.Color.blurple()
        )
        for idx, seed in enumerate(seeds):
            embed.add_field(
                name=seed.data['spoiler']['meta'].get('name', f"Game {idx}"),
                value=f"{seed.url}\n{seed.build_file_select_code(self.bot.emojis)}",
                inline=False
            )
        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def sm(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True, autocomplete=autocomplete_sm),
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
        preset: Option(str, description="The preset you want generate.", required=True, autocomplete=autocomplete_smz3),
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
        settings: Option(str, description="The settings preset you want generate.", required=True, autocomplete=autocomplete_smvaria_settings),
        skills: Option(str, description="The skills preset you want to use.", required=True, autocomplete=autocomplete_smvaria_skills),
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
    async def ctjets(self, ctx: ApplicationContext, preset: Option(str, description="The preset you want to generate.", required=True, autocomplete=autocomplete_ctjets)):
        """
        Generates a Chrono Trigger: Jets of Time randomizer game on http://ctjot.com
        """
        await ctx.defer()
        seed_uri = await generator.CTJetsPreset(preset).generate()
        await ctx.respond(seed_uri)

    z2r_group = discord.commands.SlashCommandGroup("z2r", "Generate a seed for Zelda 2 Randomizer")

    @z2r_group.command(name="preset")
    async def z2r_preset(
        self, ctx: ApplicationContext,
        preset: Option(str, description="The preset you wish to generate.", required=True, choices=z2r.Z2R_PRESETS.keys()),
    ):
        """
        Generate a Zelda 2 Randomizer game using the specified preset.
        """
        seed, flags = z2r.preset(preset)
        await ctx.respond(f"**Seed**: {seed}\n**Flags:** {flags}")

    @z2r_group.command(name="mrb")
    async def z2r_mrb(self, ctx: ApplicationContext):
        """
        Generate a seed using a random flag from the 11 in MRB's pool.
        """
        seed, flags, description = z2r.mrb()
        await ctx.respond(f"**Seed**: {seed}\n**Flags:** {flags}\n**Description**: {description}")

def get_embed_field(name: str, embed: discord.Embed) -> str:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None

def setup(bot):
    bot.add_cog(Generator(bot))
