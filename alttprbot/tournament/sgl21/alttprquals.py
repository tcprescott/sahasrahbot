import asyncio
import datetime
import random

import discord

from alttprbot import models
from alttprbot.alttprgen.preset import generate_preset, fetch_preset
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot.util import speedgaming
from alttprbot_discord.bot import discordbot
from alttprbot_racetime import bot as racetime


class ALTTPRQuals(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(307860211333595146)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="sgl21alttpr",
            coop=False,
            stream_delay=20
        )

    async def roll(self):
        triforce_text = await models.TriforceTexts.filter(broadcasted=False, pool_name='sglqual').first()

        if triforce_text is None:
            triforce_texts = await models.TriforceTexts.filter(pool_name='sglqual')
            triforce_text = random.choice(triforce_texts)

        text = triforce_text.text.encode("utf-8").decode("unicode_escape")

        self.preset_dict = await fetch_preset('sglive')
        self.preset_dict['settings']['texts'] = {}
        self.preset_dict['settings']['texts']['end_triforce'] = "{NOBORDER}\n{SPEED6}\n" + text + "\n{PAUSE9}"
        self.seed = await generate_preset(self.preset_dict, hints=False, nohints=True, spoilers='off', tournament=True)

        await self.create_embeds()

        triforce_text.broadcasted = True
        await triforce_text.save()

    async def process_tournament_race(self):
        await self.rtgg_handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        await self.update_data()
        await self.roll()

        await self.rtgg_handler.send_message(self.seed.url)

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})
        tournamentresults.permalink = self.seed.url
        await tournamentresults.save()

        await self.rtgg_handler.set_invitational()

        await self.rtgg_handler.edit(streaming_required=False)
        await self.rtgg_handler.set_raceinfo(self.race_info_rolled, overwrite=True)

        await self.rtgg_handler.send_message("Seed has been generated!  20 MINUTE STREAM DELAY REQUIRED, please check your delay!")
        self.rtgg_handler.seed_rolled = True

    @property
    def race_info_rolled(self):
        info = f"{self.seed.url} - {self.seed_code} - {self.event_name} - {self.friendly_name} - 20 MINUTE DELAY REQUIRED"
        if self.broadcast_channels:
            info += f" - Restream(s) at {', '.join(self.broadcast_channels)}"
        info += f" - {self.episodeid}"
        return info

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=False,
            unlisted=False,
            info=self.race_info,
            start_delay=30,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=False,
            allow_midrace_chat=False,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=self.data.coop,
        )
        return self.rtgg_handler

    @property
    def announce_channel(self):
        return discordbot.get_channel(307861467838021633)

    @property
    def player_racetime_ids(self):
        return []

    @property
    def seed_code(self):
        return f"({'/'.join(self.seed.code)})"

    @property
    def announce_message(self):
        msg = "{event_name} - {title} at {start_time} ({start_time_remain})".format(
            event_name=self.event_name,
            title=self.friendly_name,
            start_time=discord.utils.format_dt(self.race_start_time),
            start_time_remain=discord.utils.format_dt(self.race_start_time, "R")
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - Entry Deadline at {seed_time} - {racetime_url}".format(
            seed_time=discord.utils.format_dt(self.seed_time, "R"),
            racetime_url=self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])
        )
        return msg

    @property
    def race_info(self):
        msg = "{event_name} - {title} at {start_time} Eastern - Entry Deadline at {seed_time} - 20 MINUTE DELAY REQUIRED".format(
            event_name=self.event_name,
            title=self.friendly_name,
            start_time=self.string_time(self.race_start_time),
            seed_time=self.string_time(self.seed_time),
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - Seed Distributed at {seed_time} Eastern".format(
            seed_time=self.seed_time.astimezone(self.timezone).strftime("%-I:%M %p"),
        )
        msg += f" - {self.episodeid}"
        return msg

    @property
    def seed_time(self):
        return self.race_start_time - datetime.timedelta(minutes=10)

    async def send_player_room_info(self):
        await self.announce_channel.send(
            content=self.announce_message,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

    async def update_data(self):
        self.episode = await speedgaming.get_episode(self.episodeid)

        self.tournament_game = await models.TournamentGames.get_or_none(episode_id=self.episodeid)

        self.rtgg_bot: racetime.SahasrahBotRaceTimeBot = racetime.racetime_bots[self.data.racetime_category]
        self.restream_team = await self.rtgg_bot.get_team('sg-volunteers')
