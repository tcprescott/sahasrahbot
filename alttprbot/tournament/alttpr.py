import logging
import random
from typing import List

import discord
from racetime_bot import msg_actions

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.exceptions import SahasrahBotException
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot.util import triforce_text
from alttprbot_discord.bot import discordbot


class ALTTPRTournamentRace(TournamentRace):
    """
    ALTTPTournamentRace represets a generic ALTTP tournament
    """

    async def roll(self):
        # self.seed, self.preset_dict = await preset.get_preset('tournament', nohints=True, allow_quickswap=True)
        pass

    async def process_tournament_race(self, args, message):
        await self.rtgg_handler.send_message(
            "Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        await self.update_data()
        await self.roll()
        await self.create_embeds()

        await self.rtgg_handler.set_bot_raceinfo(self.seed_code)

        await self.send_audit_message(embed=self.embed)
        await self.send_commentary_message(self.tournament_embed)

        for name, player in self.player_discords:
            await self.send_player_message(name, player, self.embed)

        for player in self.rtgg_handler.data['entrants']:
            await self.rtgg_handler.send_message(self.seed.url, direct_to=player['user']['id'])

        tournamentresults, _ = await models.TournamentResults.update_or_create(
            srl_id=self.rtgg_handler.data.get('name'),
            defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})
        tournamentresults.permalink = self.seed.url
        await tournamentresults.save()

        await self.rtgg_handler.send_message(
            "Seed has been generated, you should have received a DM in both Discord and RaceTime.gg.  Please contact a Tournament Moderator if you haven't received the DM.")
        self.rtgg_handler.seed_rolled = True

    async def send_room_welcome(self):
        await self.rtgg_handler.send_message(
            'Welcome! Use the "Roll Tournament Seed" pinned above about 5 minutes before your race start.  You do NOT need to wait for your setup helper to do this or start your race, they will appear later to setup the stream.',
        )
        await self.rtgg_handler.send_message(
            'Tournament Controls:',
            actions=[
                msg_actions.Action(
                    label='Roll Tournament Seed',
                    help_text='Create a seed for this specific tournament race.  This should only be done shortly before the race starts.',
                    message='!tournamentrace'
                )
            ],
            pinned=True
        )

    @property
    def seed_code(self):
        return f"({'/'.join(self.seed.code)})"

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

        self.tournament_embed.insert_field_at(0, name='RaceTime.gg',
                                              value=self.rtgg_handler.bot.http_uri(self.rtgg_handler.data['url']),
                                              inline=False)
        self.embed.insert_field_at(0, name='RaceTime.gg',
                                   value=self.rtgg_handler.bot.http_uri(self.rtgg_handler.data['url']), inline=False)

        if self.broadcast_channels:
            self.tournament_embed.insert_field_at(0, name="Broadcast Channels", value=', '.join(
                [f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels]), inline=False)
            self.embed.insert_field_at(0, name="Broadcast Channels", value=', '.join(
                [f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels]), inline=False)

    async def send_race_submission_form(self, warning=False):
        if self.bracket_settings is not None and not warning:
            return

        if self.tournament_game and self.tournament_game.submitted and not warning:
            return

        if warning:
            msg = (
                f"Your upcoming race room cannot be created because settings have not submitted: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )
        else:
            msg = (
                f"Greetings!  Do not forget to submit settings for your upcoming race: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )

        for name, player in self.player_discords:
            if player is None:
                continue
            logging.info("Sending tournament submit reminder to %s.", name)
            await player.send(msg)

        await models.TournamentGames.update_or_create(episode_id=self.episodeid,
                                                      defaults={'event': self.event_slug, 'submitted': 1})


class ALTTPR2024Race(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(334795604918272012)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game - Tournament (Solo)',
            event_slug="alttpr",
            audit_channel=discordbot.get_channel(647966639266201620),
            commentary_channel=discordbot.get_channel(947095820673638400),
            scheduling_needs_channel=discordbot.get_channel(434560353461075969),
            scheduling_needs_tracker=True,
            create_scheduled_events=True,
            stream_delay=10,
            gsheet_id='1epZRDXfe-O4BBerzOEZbFMOVCFrVXU6TCDNjp66P7ZI',
            helper_roles=[
                guild.get_role(334797023054397450),
                guild.get_role(435200206552694794),
                guild.get_role(482353483853332481),
                guild.get_role(426487540829388805),
                guild.get_role(613394561594687499),
                guild.get_role(334796844750209024)
            ]
        )
