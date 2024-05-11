import io
import json

import discord
import pyz3r
import yaml
from discord import app_commands
from discord.ext import commands
from pyz3r.ext.priestmode import create_priestmode

from alttprbot import models
from alttprbot.alttprgen import generator, smvaria
from alttprbot.alttprgen.randomizer import smdash, z2r
from alttprbot.alttprgen.spoilers import (generate_spoiler_game,
                                          generate_spoiler_game_custom)
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord

# from z3rsramr import parse_sram  # pylint: disable=no-name-in-module

YES_NO_CHOICE = [
    app_commands.Choice(name="Yes", value="yes"),
    app_commands.Choice(name="No", value="no"),
]

ALTTPR_BRANCH_CHOICE = [
    app_commands.Choice(name="Live", value="live"),
    app_commands.Choice(name="Tournament", value="tournament"),
    app_commands.Choice(name="Beeta", value="beeta"),
]


class AlttprGenerator(commands.GroupCog, name="alttpr"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="preset", description="Generates an ALTTP Randomizer game on https://alttpr.com")
    @app_commands.describe(
        preset="The preset you want to generate.",
        race="Is this a race? (default no)",
        hints="Do you want hints? (default no)",
        allow_quickswap="Allow quickswap? (default yes)",
        branch="Which branch to use (default live)",
    )
    @app_commands.choices(
        race=YES_NO_CHOICE,
        hints=YES_NO_CHOICE,
        allow_quickswap=YES_NO_CHOICE,
        branch=ALTTPR_BRANCH_CHOICE,
    )
    async def preset(
            self,
            interaction: discord.Interaction,
            preset: str,
            race: str = "no",
            hints: str = "no",
            allow_quickswap: str = "yes",
            branch: str = "live",
    ):
        await interaction.response.defer()
        seed = await generator.ALTTPRPreset(preset).generate(
            hints=hints == "yes",
            spoilers="off" if race == "yes" else "on",
            tournament=race == "yes",
            allow_quickswap=allow_quickswap == "yes",
            branch=branch,
        )
        if not seed:
            raise SahasrahBotException('Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Preset", value=preset, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        description="Generates an ALTTP Randomizer game on https://alttpr.com using a custom yaml provided by the user")
    @app_commands.describe(
        yamlfile="The yaml you want to use to generate the game.",
        race="Is this a race? (default no)",
        hints="Do you want hints? (default no)",
        allow_quickswap="Allow quickswap? (default yes)",
        branch="Which branch to use (default live)"
    )
    @app_commands.choices(
        race=YES_NO_CHOICE,
        hints=YES_NO_CHOICE,
        allow_quickswap=YES_NO_CHOICE,
        branch=ALTTPR_BRANCH_CHOICE,
    )
    async def custompreset(
            self,
            interaction: discord.Interaction,
            yamlfile: discord.Attachment,
            race: str = "no",
            hints: str = "no",
            allow_quickswap: str = "yes",
            branch: str = "live",
    ):
        """
        Generates an ALTTP Randomizer game on https://alttpr.com using a custom yaml provided by the user
        """
        await interaction.response.defer()

        namespace = await generator.create_or_retrieve_namespace(interaction.user.id, interaction.user.name)

        content = await yamlfile.read()
        data = await generator.ALTTPRPreset.custom(content, f"{namespace.name}/latest")
        await data.save()
        seed = await data.generate(
            spoilers="off" if race == "yes" else "on",
            tournament=race == "yes",
            allow_quickswap=allow_quickswap == "yes",
            hints=hints == "yes",
            branch=branch,
        )

        embed: discord.Embed = await seed.embed(emojis=self.bot.emojis)
        embed.add_field(name="Saved as preset!",
                        value=f"You can generate this preset again by using the preset name of `{namespace.name}/latest`",
                        inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(description="Generates an ALTTP Randomizer Spoiler Race on https://alttpr.com")
    @app_commands.describe(preset="The preset you want to generate.")
    @app_commands.choices(
        branch=ALTTPR_BRANCH_CHOICE,
    )
    async def spoiler(
            self,
            interaction: discord.Interaction,
            preset: str,
            progression_spoiler: bool = False,
            branch: str = "live",
    ):
        await interaction.response.defer()
        spoiler = await generate_spoiler_game(
            preset,
            spoiler_type='progression' if progression_spoiler else 'spoiler',
            branch=branch
        )

        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Preset", value=preset, inline=False)
        embed.insert_field_at(0, name="Spoiler Log URL", value=spoiler.spoiler_log_url, inline=False)

        await interaction.followup.send(embed=embed)

    @preset.autocomplete("preset")
    @spoiler.autocomplete("preset")
    async def preset_autocomplete(self, interaction: discord.Interaction, current: str):
        presets = await generator.ALTTPRPreset().search(current)
        return [app_commands.Choice(name=preset, value=preset) for preset in presets]

    @app_commands.command(
        description="Generates an ALTTP Randomizer spoiler race game using a custom yaml provided by the user")
    @app_commands.describe(
        yamlfile="The yaml you want to use to generate the game."
    )
    @app_commands.choices(
        branch=ALTTPR_BRANCH_CHOICE,
    )
    async def customspoiler(
            self,
            interaction: discord.Interaction,
            yamlfile: discord.Attachment,
            branch: str = "live",
    ):
        """
        Generates an ALTTP Randomizer spoiler race game using a custom yaml provided by the user
        """
        await interaction.response.defer()

        content = await yamlfile.read()
        spoiler = await generate_spoiler_game_custom(content, branch=branch)

        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Spoiler Log URL", value=spoiler.spoiler_log_url, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(description="Generates an ALTTP Randomizer Mystery game on https://alttpr.com")
    @app_commands.describe(
        weightset="The weightset you want to use to generate the game.",
        race="Is this a race? (default no)",
        mask_settings="Mask settings? (default yes)",
    )
    @app_commands.choices(race=YES_NO_CHOICE, mask_settings=YES_NO_CHOICE)
    async def mystery(
            self,
            interaction: discord.Interaction,
            weightset: str,
            race: str = "yes",
            mask_settings: str = "yes",
    ):
        await interaction.response.defer()
        mystery = await generator.ALTTPRMystery(weightset).generate(
            spoilers="mystery" if mask_settings else "off",
            tournament=race == "yes"
        )

        embed = await mystery.seed.embed(emojis=self.bot.emojis, name="Mystery Game")

        if mystery.custom_instructions:
            embed.insert_field_at(0, name="Custom Instructions", value=mystery.custom_instructions, inline=False)
        embed.insert_field_at(0, name="Weightset", value=weightset, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        description="Generates an ALTTP Randomizer Mystery game on https://alttpr.com using a custom yaml")
    @app_commands.describe(
        yamlfile="The mystery yaml you want to use to generate the game.",
        race="Is this a race? (choosing no never masks settings) (default yes)",
        mask_settings="Mask settings? (default yes)",
    )
    @app_commands.choices(race=YES_NO_CHOICE, mask_settings=YES_NO_CHOICE)
    async def custommystery(
            self,
            interaction: discord.Interaction,
            yamlfile: discord.Attachment,
            race: str = "yes",
            mask_settings: str = "yes",
    ):
        await interaction.response.defer()

        namespace = await generator.create_or_retrieve_namespace(interaction.user.id, interaction.user.name)
        content = await yamlfile.read()
        data = await generator.ALTTPRMystery.custom(content, f"{namespace.name}/latest")
        await data.save()

        mystery = await data.generate(spoilers="mystery" if mask_settings else "off", tournament=race == "yes")

        embed = await mystery.seed.embed(emojis=self.bot.emojis, name="Mystery Game")

        if mystery.custom_instructions:
            embed.insert_field_at(0, name="Custom Instructions", value=mystery.custom_instructions, inline=False)

        embed.add_field(name="Saved as custom weightset!",
                        value=f"You can generate this weightset again by using the weightset name of `{namespace.name}/latest`.",
                        inline=False)

        await interaction.followup.send(embed=embed)

    @mystery.autocomplete("weightset")
    async def mystery_weightset_autocomplete(self, interaction: discord.Interaction, current: str):
        weightsets = await generator.ALTTPRMystery().search(current)
        return [app_commands.Choice(name=weightset, value=weightset) for weightset in weightsets]

    @app_commands.command(description="Create a series a \"Kiss Priest\" games.  This was created by hycutype.")
    @app_commands.describe(
        count="The number of games you want to generate.  Default is 10.",
    )
    async def kisspriest(
            self,
            interaction: discord.Interaction,
            count: app_commands.Range[int, 1, 10] = 10,
    ):
        await interaction.response.defer()

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
        await interaction.followup.send(embed=embed)


class AlttprUtils(commands.GroupCog, name="alttprutils", description="Utilities for the ALTTP Randomizer"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # @app_commands.command(description="Outputs stats about an ALTTP Randomizer sram file.")
    # @app_commands.describe(sram="A valid ALTTPR SRAM file.", raw="Output raw json instead of a pretty embed.")
    # async def stats(
    #     self,
    #     interaction: discord.Interaction,
    #     sram: discord.Attachment,
    #     raw: bool=False,
    # ):
    #     """
    #     Outputs stats about an ALTTP Randomizer sram file
    #     """
    #     parsed = parse_sram(await sram.read())
    #     if raw:
    #         await interaction.response.send_message(
    #             file=discord.File(
    #                 io.StringIO(json.dumps(parsed, indent=4)),
    #                 filename=f"stats_{parsed['meta'].get('filename', 'alttpr').strip()}.txt"
    #             )
    #         )
    #     else:
    #         embed = discord.Embed(
    #             title=f"ALTTPR Stats for \"{parsed['meta'].get('filename', '').strip()}\"",
    #             description=f"Collection Rate {parsed['stats'].get('collection rate')}",
    #             color=discord.Color.blue()
    #         )
    #         embed.add_field(
    #             name="Time",
    #             value=(
    #                 f"Total Time: {parsed['stats'].get('total time', None)}\n"
    #                 f"Lag Time: {parsed['stats'].get('lag time', None)}\n"
    #                 f"Menu Time: {parsed['stats'].get('menu time', None)}\n\n"
    #                 f"First Sword: {parsed['stats'].get('first sword', None)}\n"
    #                 f"Flute Found: {parsed['stats'].get('flute found', None)}\n"
    #                 f"Mirror Found: {parsed['stats'].get('mirror found', None)}\n"
    #                 f"Boots Found: {parsed['stats'].get('boots found', None)}\n"
    #             ),
    #             inline=False
    #         )
    #         embed.add_field(
    #             name="Important Stats",
    #             value=(
    #                 f"Bonks: {parsed['stats'].get('bonks', None)}\n"
    #                 f"Deaths: {parsed['stats'].get('deaths', None)}\n"
    #                 f"Revivals: {parsed['stats'].get('faerie revivals', None)}\n"
    #                 f"Overworld Mirrors: {parsed['stats'].get('overworld mirrors', None)}\n"
    #                 f"Rupees Spent: {parsed['stats'].get('rupees spent', None)}\n"
    #                 f"Save and Quits: {parsed['stats'].get('save and quits', None)}\n"
    #                 f"Screen Transitions: {parsed['stats'].get('screen transitions', None)}\n"
    #                 f"Times Fluted: {parsed['stats'].get('times fluted', None)}\n"
    #                 f"Underworld Mirrors: {parsed['stats'].get('underworld mirrors', None)}\n"
    #             )
    #         )
    #         embed.add_field(
    #             name="Misc Stats",
    #             value=(
    #                 f"Swordless Bosses: {parsed['stats'].get('swordless bosses', None)}\n"
    #                 f"Fighter Sword Bosses: {parsed['stats'].get('fighter sword bosses', None)}\n"
    #                 f"Master Sword Bosses: {parsed['stats'].get('master sword bosses', None)}\n"
    #                 f"Tempered Sword Bosses: {parsed['stats'].get('tempered sword bosses', None)}\n"
    #                 f"Golden Sword Bosses: {parsed['stats'].get('golden sword bosses', None)}\n\n"
    #                 f"Heart Containers: {parsed['stats'].get('heart containers', None)}\n"
    #                 f"Heart Containers: {parsed['stats'].get('heart pieces', None)}\n"
    #                 f"Mail Upgrade: {parsed['stats'].get('mails', None)}\n"
    #                 f"Bottles: {parsed['equipment'].get('bottles', None)}\n"
    #                 f"Silver Arrows: {parsed['equipment'].get('silver arrows', None)}\n"
    #             )
    #         )
    #         if not parsed.get('hash id', 'none') == 'none':
    #             seed = await ALTTPRDiscord.retrieve(hash_id=parsed.get('hash id', 'none'))
    #             embed.add_field(name='File Select Code', value=seed.build_file_select_code(
    #                 emojis=self.bot.emojis
    #             ), inline=False)
    #             embed.add_field(name='Permalink', value=seed.url, inline=False)

    #         await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(description="Convert a customizer save file to a SahasrahBot preset file.")
    @app_commands.describe(customizer_json="A valid ALTTPR Customizer save file.")
    async def convertcustomizer(self, interaction: discord.Interaction, customizer_json: discord.Attachment):
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
        await interaction.response.send_message(
            file=discord.File(
                io.StringIO(yaml.dump(preset_dict)),
                filename="output.yaml"
            ),
            ephemeral=True
        )

    @app_commands.command(description="Save a preset to your namespace.")
    @app_commands.describe(
        preset_name="The name of the preset to save.",
        preset_file="A valid SahasrahBot preset file."
    )
    async def savepreset(
            self,
            interaction: discord.Interaction,
            preset_name: str,
            preset_file: discord.Attachment
    ):
        """
        Save a preset to your namespace.
        """
        namespace = await generator.create_or_retrieve_namespace(interaction.user.id, interaction.user.name)

        content = await preset_file.read()
        data = await generator.ALTTPRPreset.custom(content, f"{namespace.name}/{preset_name}")
        await data.save()

        await interaction.response.send_message(f"Preset saved as {data.namespace}/{data.preset}", ephemeral=True)

    @app_commands.command(description="Verify a game was generated by SahasrahBot.")
    @app_commands.describe(
        hash_id="The hash ID of the game to verify."
    )
    async def verifygame(
            self, interaction: discord.Interaction,
            hash_id: str
    ):
        """
        Verify a game was generated by SahasrahBot.
        """
        result = await models.AuditGeneratedGames.get_or_none(hash_id=hash_id)
        if not result:
            await interaction.response.send_message("That game was not generated by SahasrahBot.")
            return

        await interaction.response.send_message((
            f"{hash_id} was generated by SahasrahBot.\n\n"
            f"**Randomizer:** {result.randomizer}\n"
            f"**Game Type:** {result.gentype}\n"
            f"**Game Option:** {result.genoption}\n\n"
            f"**Permalink:** <{result.permalink}>"
        ), ephemeral=True)


class Generator(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(description="Generates an Super Metroid Randomizer game on https://sm.samus.link")
    @app_commands.describe(
        preset="The preset you want generate.",
        race="Is this a race? (default no)"
    )
    @app_commands.choices(race=YES_NO_CHOICE)
    async def sm(
            self,
            interaction: discord.Interaction,
            preset: str,
            race: str = "no",
    ):
        """
        Generates an Super Metroid Randomizer game on https://sm.samus.link
        """
        await interaction.response.defer()
        smpreset = generator.SMPreset(preset)
        await smpreset.generate(tournament=race == "yes", spoilers=False)
        embed = await smpreset.seed.embed()
        await interaction.followup.send(embed=embed)

    @sm.autocomplete("preset")
    async def sm_autocomplete(self, interaction: discord.Interaction, current: str):
        presets = await generator.SMPreset().search(current)
        return [app_commands.Choice(name=preset, value=preset) for preset in presets]

    @app_commands.command()
    @app_commands.describe(
        preset="The preset you want generate.",
        race="Is this a race? (default no)"
    )
    @app_commands.choices(race=YES_NO_CHOICE, spoiler_race=YES_NO_CHOICE)
    async def smz3(
            self,
            interaction: discord.Interaction,
            preset: str,
            race: str = "no",
            spoiler_race: str = "no",
    ):
        """
        Generates an ALTTP Super Metroid Combo Randomizer game on https://samus.link
        """
        await interaction.response.defer()
        smz3preset = generator.SMZ3Preset(preset)
        await smz3preset.generate(tournament=race == "yes", spoilers=spoiler_race == "yes")
        embed = await smz3preset.seed.embed()
        if spoiler_url := smz3preset.spoiler_url():
            embed.add_field(name='Race Spoiler Log', value=spoiler_url)
        await interaction.followup.send(embed=embed)

    @smz3.autocomplete("preset")
    async def smz3_autocomplete(self, interaction: discord.Interaction, current: str):
        presets = await generator.SMZ3Preset().search(current)
        return [app_commands.Choice(name=preset, value=preset) for preset in presets]

    @app_commands.command()
    @app_commands.describe(
        settings="The settings preset you want generate.",
        skills="The skills you want to use.",
        race="Is this a race? (default no)"
    )
    @app_commands.choices(race=YES_NO_CHOICE)
    async def smvaria(
            self,
            interaction: discord.Interaction,
            settings: str,
            skills: str,
            race: str = "no",
    ):
        """
        Generates an Super Metroid Varia Randomizer game on https://varia.run
        """
        await interaction.response.defer()
        seed = await smvaria.generate_preset(
            settings=settings,
            skills=skills,
            race=race == "yes"
        )
        await interaction.followup.send(embed=seed.embed())

    @smvaria.autocomplete("skills")
    async def autocomplete_smvaria_skills(self, interaction: discord.Interaction, current: str):
        skills = ['SMRAT2021', 'Season_Races', 'Torneio_SGPT2', 'casual', 'expert', 'master', 'newbie', 'regular',
                  'samus', 'solution', 'veteran']
        return sorted([a for a in skills if a.startswith(current)][:25])

    @smvaria.autocomplete("settings")
    async def autocomplete_smvaria_settings(self, interaction: discord.Interaction, current: str):
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
        return sorted([a for a in settings if a.startswith(current)][:25])

    @app_commands.command()
    @app_commands.describe(
        preset="The preset you want to generate.",
        spoiler="Generate a spoiler log? (default no)"
    )
    @app_commands.choices(spoiler=YES_NO_CHOICE)
    async def smdash(
            self,
            interaction: discord.Interaction,
            preset: str,
            spoiler: str = "no"
    ):
        """
        Generates a Super Metroid Dash Randomizer game on https://dashrando.net
        """
        await interaction.response.defer()
        url = await smdash.create_smdash(mode=preset, spoiler=spoiler == "yes")
        await interaction.followup.send(url)
    @smdash.autocomplete("preset")
    async def smdash_preset_autocomplete(self, interaction: discord.Interaction, current: str):
        presets = await smdash.get_smdash_presets()
        filtered = sorted([a for a in presets if a.startswith(current.lower())][:25])
        return [app_commands.Choice(name=preset, value=preset) for preset in filtered]

    @app_commands.command()
    @app_commands.describe(
        preset="The preset you want to generate."
    )
    async def ctjets(
            self,
            interaction: discord.Interaction,
            preset: str
    ):
        """
        Generates a Chrono Trigger: Jets of Time randomizer game on http://ctjot.com
        """
        await interaction.response.defer()
        seed_uri = await generator.CTJetsPreset(preset).generate()
        await interaction.followup.send(seed_uri)

    @ctjets.autocomplete("preset")
    async def ctjets_autocomplete(self, interaction: discord.Interaction, current: str):
        presets = await generator.CTJetsPreset().search(current)
        return [app_commands.Choice(name=preset, value=preset) for preset in presets]


class Z2RGenerator(commands.GroupCog, name="z2r", description="Generate a seed for Zelda 2 Randomizer"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        preset="The preset you want to generate."
    )
    @app_commands.choices(preset=[app_commands.Choice(name=preset, value=preset) for preset in z2r.Z2R_PRESETS.keys()])
    async def preset(
            self,
            interaction: discord.Interaction,
            preset: str,
    ):
        """
        Generate a Zelda 2 Randomizer game using the specified preset.
        """
        seed, flags = z2r.preset(preset)
        await interaction.response.send_message(f"**Seed**: {seed}\n**Flags:** {flags}")

    @app_commands.command()
    async def mrb(self, interaction: discord.Interaction):
        """
        Generate a seed using a random flag from the 11 in MRB's pool.
        """
        seed, flags, description = z2r.mrb()
        await interaction.response.send_message(f"**Seed**: {seed}\n**Flags:** {flags}\n**Description**: {description}")


def get_embed_field(name: str, embed: discord.Embed) -> str:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None


async def setup(bot: commands.Bot):
    await bot.add_cog(AlttprGenerator(bot))
    await bot.add_cog(AlttprUtils(bot))
    await bot.add_cog(Generator(bot))
    await bot.add_cog(Z2RGenerator(bot))
