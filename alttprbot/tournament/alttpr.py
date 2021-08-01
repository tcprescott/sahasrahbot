import logging

import discord

from alttprbot.alttprgen import preset
from alttprbot import models
from alttprbot.tournament.core import TournamentRace
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord

class ALTTPRTournamentRace(TournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('tournament', nohints=True, allow_quickswap=True)
        await self.create_embeds()

    async def process_tournament_race(self):
        await self.rtgg_handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        await self.roll()

        await self.rtgg_handler.set_raceinfo(self.race_info_rolled, overwrite=True)

        await self.send_audit_message(self.embed)
        await self.send_commentary_message(self.tournament_embed)

        for name, player in self.player_discords:
            await self.send_player_message(name, player, self.embed)

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})
        tournamentresults.permalink = self.seed.url
        await tournamentresults.save()

        await self.rtgg_handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a Tournament Moderator if you haven't received the DM.")
        self.rtgg_handler.seed_rolled = True

    async def send_room_welcome(self):
        await self.rtgg_handler.send_message('Welcome. Use !tournamentrace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of your race.')

    @property
    def seed_code(self):
        if isinstance(self.seed.code, list):
            return f"({'/'.join(self.seed.code)})"
        elif isinstance(self.seed.code, str):
            return f"({self.seed.code})"

        return ""

    @property
    def bracket_settings(self):
        return None

    async def create_embeds(self):
        if self.rtgg_handler is None:
            raise SahasrahBotException("No RaceTime.gg handler associated with this tournament game.")

        self.embed = await self.seed.embed(
            name=self.race_info,
            notes=self.versus,
            emojis=discordbot.emojis
        )

        self.tournament_embed = await self.seed.tournament_embed(
            name=self.race_info,
            notes=self.versus,
            emojis=discordbot.emojis
        )

        self.tournament_embed.insert_field_at(0, name='RaceTime.gg', value=self.rtgg_handler.bot.http_uri(self.rtgg_handler.data['url']), inline=False)
        self.embed.insert_field_at(0, name='RaceTime.gg', value=self.rtgg_handler.bot.http_uri(self.rtgg_handler.data['url']), inline=False)

        if self.broadcast_channels:
            self.tournament_embed.insert_field_at(0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels]), inline=False)
            self.embed.insert_field_at(0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels]), inline=False)
