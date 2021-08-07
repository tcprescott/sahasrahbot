import logging

import discord

from alttprbot.alttprgen import preset
from alttprbot import models
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord

class ALTTPRESTournament(ALTTPRTournamentRace):
    async def roll(self):
        if self.bracket_settings is None:
            raise Exception('Missing bracket settings.  Please submit!')

        self.preset_dict = None
        self.seed = await alttpr_discord.ALTTPRDiscord.generate(
            settings=self.bracket_settings,
            endpoint='/api/customizer' if 'eq' in self.bracket_settings else '/api/randomizer',
        )
        await self.create_embeds()

    async def configuration(self):
        guild = discordbot.get_guild(477850508368019486)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttpres",
            audit_channel=discordbot.get_channel(859058002426462211),
            commentary_channel=discordbot.get_channel(838011943000080395),
            scheduling_needs_channel=discordbot.get_channel(863771537903714324),
            scheduling_needs_tracker=True,
            helper_roles=[
                guild.get_role(479423657584754698),
                guild.get_role(477968190606016528),
            ],
            lang="es"
        )

    @property
    def bracket_settings(self):
        if self.tournament_game:
            return self.tournament_game.settings

        return None

    @property
    def submission_form(self):
        return [
            {
                'key': 'preset',
                'label': 'Preset',
                'settings': {
                    'ambrosia': 'Ambrosia',
                    'casualboots': 'Casual Boots',
                    'mcs': 'Maps, Compasses, and Small Keys',
                    'open': 'Open',
                    'standard': 'Standard',
                    'adkeys': "All Dungeons + Keysanity (Round of 8 only)",
                    'dungeons': 'All Dungeons (Round of 8 only)',
                    'keysanity': 'Keysanity (Round of 8 only)',
                }
            }
        ]

    async def process_submission_form(self, payload, submitted_by):
        embed = discord.Embed(
            title=f"ALTTPR ES - {self.versus}",
            description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
            color=discord.Colour.blue()
        )

        preset_dict = await preset.fetch_preset(payload['preset'])

        preset_dict['tournament'] = True
        preset_dict['allow_quickswap'] = True
        preset_dict['spoilers'] = 'off'

        embed.add_field(name="Preset", value=payload['preset'], inline=False)

        embed.add_field(name="Submitted by", value=submitted_by, inline=False)

        await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'settings': preset_dict['settings'], 'event': 'alttpres'})

        if self.audit_channel:
            await self.audit_channel.send(embed=embed)

        for name, player in self.player_discords:
            if player is None:
                logging.error(f"Could not send DM to {name}")
                if self.audit_channel:
                    await self.audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
                continue
            try:
                await player.send(embed=embed)
            except discord.HTTPException:
                logging.exception(f"Could not send DM to {name}")
                if self.audit_channel:
                    await self.audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
