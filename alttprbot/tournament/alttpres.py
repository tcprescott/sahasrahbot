import logging

import discord

from alttprbot.alttprgen import preset
from alttprbot.tournaments import fetch_tournament_handler
from alttprbot import models
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
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

    @property
    def bracket_settings(self):
        if self.tournament_game:
            return self.tournament_game.settings

        return None

    async def process_submission_form(self, payload, submitted_by):
        episode_id = int(payload['episodeid'])

        tournament_race = await fetch_tournament_handler("alttpres", episode_id)

        embed = discord.Embed(
            title=f"ALTTPR ES - {tournament_race.versus}",
            description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
            color=discord.Colour.blue()
        )

        preset_dict = await preset.fetch_preset(payload['preset'])

        preset_dict['tournament'] = True
        preset_dict['allow_quickswap'] = True
        preset_dict['spoilers'] = 'off'

        embed.add_field(name="Preset", value=payload['preset'], inline=False)

        embed.add_field(name="Submitted by", value=submitted_by, inline=False)

        await models.TournamentGames.update_or_create(episode_id=episode_id, defaults={'settings': preset_dict['settings'], 'event': 'alttpres'})

        audit_channel_id = tournament_race.data.audit_channel_id
        if audit_channel_id is not None:
            audit_channel = discordbot.get_channel(audit_channel_id)
            await audit_channel.send(embed=embed)
        else:
            audit_channel = None

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


        return tournament_race

