import logging

import discord

from alttprbot import models
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot_discord.util import alttpr_discord

class ALTTPRFRTournament(ALTTPRTournamentRace):
    async def roll(self):
        if self.bracket_settings is None:
            raise Exception('Missing bracket settings.  Please submit!')

        self.preset_dict = None
        self.seed = await alttpr_discord.ALTTPRDiscord.generate(settings=self.bracket_settings)
        await self.create_embeds()

    @property
    def bracket_settings(self):
        if self.tournament_game:
            return self.tournament_game.settings

        return None

    async def process_submission_form(self, payload, submitted_by):
        adjusted_payload = payload.to_dict(flat=True)

        embed = discord.Embed(
            title=f"ALTTPR FR - {self.versus}",
            description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
            color=discord.Colour.blue()
        )

        if adjusted_payload['enemy_shuffle'] != "none" and adjusted_payload['world_state'] == 'standard' and adjusted_payload['swords'] in ['randomized', 'swordless']:
            adjusted_payload['swords'] = 'assured'

        settings = {
            "glitches": "none",
            "item_placement": "advanced",
            "dungeon_items": adjusted_payload.get("dungeon_items", "standard"),
            "accessibility": "items",
            "goal": adjusted_payload.get("goal", "ganon"),
            "crystals": {
                "ganon": "7",
                "tower": "7"
            },
            "mode": adjusted_payload.get("world_state", "mode"),
            "entrances": "none",
            "hints": adjusted_payload.get("hints", "off"),
            "weapons": adjusted_payload.get("swords", "randomized"),
            "item": {
                "pool": adjusted_payload.get("item_pool", "normal"),
                "functionality": adjusted_payload.get("item_functionality", "normal"),
            },
            "tournament": True,
            "spoilers": "off",
            "lang": "en",
            "enemizer": {
                "boss_shuffle": adjusted_payload.get("boss_shuffle", "none"),
                "enemy_shuffle": adjusted_payload.get("enemy_shuffle", "none"),
                "enemy_damage": "default",
                "enemy_health": "default",
                "pot_shuffle": "off"
            },
            "allow_quickswap": True
        }

        settings_formatted = ""
        for setting in self.data.settings_form:
            settings_formatted += f"**{setting['label']}:** {setting['settings'][adjusted_payload.get(setting['key'])]}\n"

        embed.add_field(name="Settings", value=settings_formatted, inline=False)

        embed.add_field(name="Submitted by", value=submitted_by, inline=False)

        await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'settings': settings, 'event': 'alttprfr'})

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
