import io
import json

import discord
import pyz3r
import yaml

from alttprbot import models
from alttprbot.alttprgen import generator, smvaria
from alttprbot.alttprgen.randomizer import smdash, z2r
from alttprbot.alttprgen.spoilers import (generate_spoiler_game,
                                          generate_spoiler_game_custom)
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord
from alttprbot_discord.util.alttprdoors_discord import AlttprDoorDiscord
from discord.commands import ApplicationContext, Option
from discord.ext import commands
from pyz3r.ext.priestmode import create_priestmode
from z3rsramr import parse_sram  # pylint: disable=no-name-in-module


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
        await respmsg.edit_original_message(content=None, embed=embed)


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
    alttprutils = discord.commands.SlashCommandGroup("alttprutils", "Utilities for the ALTTP Randomizer")

    @alttpr.command()
    async def preset(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True, autocomplete=autocomplete_alttpr),
        race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no"),
        hints: Option(str, description="Enable hints? (default no)", choices=["yes", "no"], required=False, default="no"),
        allow_quickswap: Option(str, description="Allow quickswap? (default yes)", choices=["yes", "no"], required=False, default="yes"),
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

        await ctx.respond(embed=embed)

    @alttpr.command()
    async def custompreset(
        self,
        ctx: ApplicationContext,
        yamlfile: Option(discord.Attachment, description="The preset you want generate.", required=True),
        race: Option(str, description="Is this a race? (default no)", choices=["yes", "no"], required=False, default="no"),
        hints: Option(str, description="Enable hints? (default no)", choices=["yes", "no"], required=False, default="no"),
        allow_quickswap: Option(str, description="Allow quickswap? (default yes)", choices=["yes", "no"], required=False, default="yes"),
    ):
        """
        Generates an ALTTP Randomizer game on https://alttpr.com using a custom yaml provided by the user
        """
        await ctx.defer()

        namespace = await generator.create_or_retrieve_namespace(ctx.author.id, ctx.author.name)

        content = await yamlfile.read()
        data = await generator.ALTTPRPreset.custom(content, f"{namespace.name}/latest")
        await data.save()
        seed = await data.generate(
            spoilers="off" if race == "yes" else "on",
            tournament=race == "yes",
            allow_quickswap=allow_quickswap == "yes",
            hints=hints == "yes"
        )

        embed: discord.Embed = await seed.embed(emojis=self.bot.emojis)
        embed.add_field(name="Saved as preset!", value=f"You can generate this preset again by using the preset name of `{namespace.name}/latest`", inline=False)

        await ctx.respond(embed=embed)

    @alttpr.command()
    async def spoiler(
        self,
        ctx: ApplicationContext,
        preset: Option(str, description="The preset you want generate.", required=True, autocomplete=autocomplete_alttpr),
    ):
        """
        Generates an ALTTP Randomizer Spoiler Race on https://alttpr.com
        """
        await ctx.defer()
        spoiler = await generate_spoiler_game(preset)

        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Preset", value=preset, inline=False)
        embed.insert_field_at(0, name="Spoiler Log URL", value=spoiler.spoiler_log_url, inline=False)

        await ctx.respond(embed=embed)

    @alttpr.command()
    async def customspoiler(
        self,
        ctx: ApplicationContext,
        yamlfile: Option(discord.Attachment, description="A valid preset yaml file.", required=True),
    ):
        """
        Generates an ALTTP Randomizer spoiler race game using a custom yaml provided by the user
        """
        await ctx.defer()

        content = await yamlfile.read()
        spoiler = await generate_spoiler_game_custom(content)

        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
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
    async def custommystery(
        self,
        ctx: ApplicationContext,
        yamlfile: Option(discord.Attachment, description="A valid mystery yaml file.", required=True),
        race: Option(str, description="Is this a race? (choosing no never masks settings) (default yes)", choices=["yes", "no"], required=False, default="yes"),
        mask_settings: Option(str, description="Mask settings? (default yes)", choices=["yes", "no"], required=False, default="yes"),
    ):
        """
        Generates an ALTTP Randomizer Mystery game on https://alttpr.com using a custom yaml
        """
        await ctx.defer()

        namespace = await generator.create_or_retrieve_namespace(ctx.author.id, ctx.author.name)
        content = await yamlfile.read()
        data = await generator.ALTTPRMystery.custom(content, f"{namespace.name}/latest")
        await data.save()

        mystery = await data.generate(spoilers="mystery" if mask_settings else "off", tournament=race == "yes")

        embed = await mystery.seed.embed(emojis=ctx.bot.emojis, name="Mystery Game")

        if mystery.custom_instructions:
            embed.insert_field_at(0, name="Custom Instructions", value=mystery.custom_instructions, inline=False)

        embed.add_field(name="Saved as custom weightset!", value=f"You can generate this weightset again by using the weightset name of `{namespace.name}/latest`.", inline=False)

        await ctx.respond(embed=embed)

    @alttprutils.command()
    async def stats(
        self,
        ctx: ApplicationContext,
        sram: Option(discord.Attachment, description="A valid ALTTPR sram file.", required=True),
        raw: Option(bool, description="Output raw stats?", required=False, default=False),
    ):
        """
        Outputs stats about an ALTTP Randomizer sram file
        """
        parsed = parse_sram(await sram.read())
        if raw:
            await ctx.respond(
                file=discord.File(
                    io.StringIO(json.dumps(parsed, indent=4)),
                    filename=f"stats_{parsed['meta'].get('filename', 'alttpr').strip()}.txt"
                )
            )
        else:
            embed = discord.Embed(
                title=f"ALTTPR Stats for \"{parsed['meta'].get('filename', '').strip()}\"",
                description=f"Collection Rate {parsed['stats'].get('collection rate')}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Time",
                value=(
                    f"Total Time: {parsed['stats'].get('total time', None)}\n"
                    f"Lag Time: {parsed['stats'].get('lag time', None)}\n"
                    f"Menu Time: {parsed['stats'].get('menu time', None)}\n\n"
                    f"First Sword: {parsed['stats'].get('first sword', None)}\n"
                    f"Flute Found: {parsed['stats'].get('flute found', None)}\n"
                    f"Mirror Found: {parsed['stats'].get('mirror found', None)}\n"
                    f"Boots Found: {parsed['stats'].get('boots found', None)}\n"
                ),
                inline=False
            )
            embed.add_field(
                name="Important Stats",
                value=(
                    f"Bonks: {parsed['stats'].get('bonks', None)}\n"
                    f"Deaths: {parsed['stats'].get('deaths', None)}\n"
                    f"Revivals: {parsed['stats'].get('faerie revivals', None)}\n"
                    f"Overworld Mirrors: {parsed['stats'].get('overworld mirrors', None)}\n"
                    f"Rupees Spent: {parsed['stats'].get('rupees spent', None)}\n"
                    f"Save and Quits: {parsed['stats'].get('save and quits', None)}\n"
                    f"Screen Transitions: {parsed['stats'].get('screen transitions', None)}\n"
                    f"Times Fluted: {parsed['stats'].get('times fluted', None)}\n"
                    f"Underworld Mirrors: {parsed['stats'].get('underworld mirrors', None)}\n"
                )
            )
            embed.add_field(
                name="Misc Stats",
                value=(
                    f"Swordless Bosses: {parsed['stats'].get('swordless bosses', None)}\n"
                    f"Fighter Sword Bosses: {parsed['stats'].get('fighter sword bosses', None)}\n"
                    f"Master Sword Bosses: {parsed['stats'].get('master sword bosses', None)}\n"
                    f"Tempered Sword Bosses: {parsed['stats'].get('tempered sword bosses', None)}\n"
                    f"Golden Sword Bosses: {parsed['stats'].get('golden sword bosses', None)}\n\n"
                    f"Heart Containers: {parsed['stats'].get('heart containers', None)}\n"
                    f"Heart Containers: {parsed['stats'].get('heart pieces', None)}\n"
                    f"Mail Upgrade: {parsed['stats'].get('mails', None)}\n"
                    f"Bottles: {parsed['equipment'].get('bottles', None)}\n"
                    f"Silver Arrows: {parsed['equipment'].get('silver arrows', None)}\n"
                )
            )
            if not parsed.get('hash id', 'none') == 'none':
                seed = await ALTTPRDiscord.retrieve(hash_id=parsed.get('hash id', 'none'))
                embed.add_field(name='File Select Code', value=seed.build_file_select_code(
                    emojis=ctx.bot.emojis
                ), inline=False)
                embed.add_field(name='Permalink', value=seed.url, inline=False)

            await ctx.respond(embed=embed, ephemeral=True)

    @alttprutils.command()
    async def convertcustomizer(self, ctx: ApplicationContext, customizer_json: Option(discord.Attachment, description="A valid customizer save file.", required=True)):
        """
        Convert a customizer save file to a SahasrahBot preset file.
        """
        content = await customizer_json.read()
        customizer_save = json.loads(content)
        settings = pyz3r.customizer.convert2settings(customizer_save)
        preset_dict = {
            'customizer': True,
            'randomizer': 'alttpr',
            'settings': settings
        }
        await ctx.respond(
            file=discord.File(
                io.StringIO(yaml.dump(preset_dict)),
                filename="output.yaml"
            ),
            ephemeral=True
        )

    @alttprutils.command()
    async def savepreset(
        self,
        ctx: ApplicationContext,
        preset_name: Option(str, description="The name of the preset.", required=True),
        preset_file: Option(discord.Attachment, description="A valid preset file.", required=True)
    ):
        """
        Save a preset to your namespace.
        """
        namespace = await generator.create_or_retrieve_namespace(ctx.author.id, ctx.author.name)

        content = await preset_file.read()
        data = await generator.ALTTPRPreset.custom(content, f"{namespace.name}/{preset_name}")
        await data.save()

        await ctx.respond(f"Preset saved as {data.namespace}/{data.preset}", ephemeral=True)

    @alttprutils.command()
    async def verifygame(self, ctx: ApplicationContext, hash_id: Option(str, description="The hash id of the game you want to verify.", required=True)):
        """
        Verify a game was generated by SahasrahBot.
        """
        result = await models.AuditGeneratedGames.get_or_none(hash_id=hash_id)
        if not result:
            await ctx.reply("That game was not generated by SahasrahBot.")
            return

        await ctx.respond((
            f"{hash_id} was generated by SahasrahBot.\n\n"
            f"**Randomizer:** {result.randomizer}\n"
            f"**Game Type:** {result.gentype}\n"
            f"**Game Option:** {result.genoption}\n\n"
            f"**Permalink:** <{result.permalink}>"
        ), ephemeral=True)

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
