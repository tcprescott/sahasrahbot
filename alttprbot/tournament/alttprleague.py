# import discord
import logging

import aiohttp
# from alttprbot import models
from alttprbot.alttprgen import preset, spoilers
from alttprbot.database import spoiler_races  # TODO switch to ORM
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot


class ALTTPRLeague(ALTTPRTournamentRace):
    async def roll(self):
        if self.week_data.get('spoiler', False):
            spoiler = await spoilers.generate_spoiler_game(self.week_data['preset'])
            await spoiler_races.insert_spoiler_race(self.rtgg_handler.data.get('name'), spoiler.spoiler_log_url, 0)
        else:
            self.seed, self.preset_dict = await preset.get_preset(self.week_data['preset'], allow_quickswap=True)

        await self.create_embeds()

    async def get_week(self):
        async with aiohttp.request('get', 'https://alttprleague.com/api/week') as req:
            week_response = await req.json()

        try:
            self.week_data = week_response.get('weeks', [])[0]
        except IndexError:
            logging.exception("No active league week!")
            await self.rtgg_handler.send_message("No active League Week!  This should not have happened.  Contact a league admin/mod for help.")

    async def update_data(self):
        await super().update_data()
        await self.get_week()

    async def configuration(self):
        guild = discordbot.get_guild(543577975032119296)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="invleague",
            audit_channel=discordbot.get_channel(546728638272241674),
            commentary_channel=discordbot.get_channel(611601587139510322),
            scheduling_needs_channel=discordbot.get_channel(878075812996337744),
            scheduling_needs_tracker=True,
            helper_roles=[
                guild.get_role(543596853871116288),
                guild.get_role(543597099649073162),
                guild.get_role(676530377812082706),
                guild.get_role(553295025190993930),
                guild.get_role(674109759179194398),
            ]
        )

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=True,
            unlisted=False,
            info=self.race_info,
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=self.week_data.get('coop', False),
        )
        return self.rtgg_handler

    # @property
    # def bracket_settings(self):
    #     if self.tournament_game:
    #         return self.tournament_game.settings

    #     return None

    # @property
    # def submission_form(self):
    #     return [
    #         {
    #             'key': 'game',
    #             'label': 'Game #',
    #             'settings': {
    #                 '1': '1',
    #                 '2': '2',
    #                 '3': '3',
    #                 '4': '4',
    #                 '5': '5',
    #             }
    #         },
    #         {
    #             'key': 'preset',
    #             'label': 'Preset',
    #             'required_if': {
    #                 'game': ['3', '4', '5']
    #             },
    #             'settings': {
    #                 'default': 'Game 1 or 2',
    #                 'invrosia': 'Invrosia',
    #                 'champions_swordless': 'Champion\'s Swordless',
    #                 'hard_mc': 'Open Hard MC Shuffle',
    #                 'hard_enemizer': 'Open Hard Enemizer',
    #             }
    #         }
    #     ]

    # async def process_submission_form(self, payload, submitted_by):
    #     embed = discord.Embed(
    #         title=f"ALTTPR League - {self.versus}",
    #         description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
    #         color=discord.Colour.blue()
    #     )

    #     if payload['game'] == '1':
    #         preset_name = 'casual_boots'
    #     elif payload['game'] == '2':
    #         preset_name = 'crosskeys'
    #     else:
    #         if payload['preset'] == 'default':
    #             raise Exception('Must choose a preset for games 3, 4, or 5.')
    #         preset_name = payload['preset']

    #     preset_dict = await preset.fetch_preset(preset_name)

    #     preset_dict['tournament'] = True
    #     preset_dict['allow_quickswap'] = True
    #     preset_dict['spoilers'] = 'off'

    #     embed.add_field(name="Preset", value=payload['preset'], inline=False)

    #     embed.add_field(name="Submitted by", value=submitted_by, inline=False)

    #     await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'settings': preset_dict['settings'], 'event': self.event_slug})

    #     if self.audit_channel:
    #         await self.audit_channel.send(embed=embed)

    #     for name, player in self.player_discords:
    #         if player is None:
    #             logging.error(f"Could not send DM to {name}")
    #             if self.audit_channel:
    #                 await self.audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
    #             continue
    #         try:
    #             await player.send(embed=embed)
    #         except discord.HTTPException:
    #             logging.exception(f"Could not send DM to {name}")
    #             if self.audit_channel:
    #                 await self.audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)


class ALTTPROpenLeague(ALTTPRLeague):
    async def configuration(self):
        guild = discordbot.get_guild(543577975032119296)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttprleague",
            audit_channel=discordbot.get_channel(546728638272241674),
            commentary_channel=discordbot.get_channel(611601587139510322),
            scheduling_needs_channel=discordbot.get_channel(878076083193389096),
            scheduling_needs_tracker=True,
            helper_roles=[
                guild.get_role(543596853871116288),
                guild.get_role(543597099649073162),
                guild.get_role(676530377812082706),
                guild.get_role(553295025190993930),
                guild.get_role(674109759179194398),
            ]
        )
