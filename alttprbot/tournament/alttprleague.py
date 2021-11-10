import discord
import logging

# import aiohttp
# import tortoise.exceptions
from alttprbot import models
from alttprbot.alttprgen import preset #, spoilers
# from alttprbot.database import spoiler_races  # TODO switch to ORM
from alttprbot.alttprgen import generator
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot


class ALTTPRLeague(ALTTPRTournamentRace):
    settings_data: models.TournamentGames = None

    # async def roll(self):
    #     if self.week_data.get('spoiler', False):
    #         spoiler = await spoilers.generate_spoiler_game(self.week_data['preset'])
    #         await spoiler_races.insert_spoiler_race(self.rtgg_handler.data.get('name'), spoiler.spoiler_log_url, 0)
    #     else:
    #         self.seed, self.preset_dict = await preset.get_preset(self.week_data['preset'], allow_quickswap=True)

    #     await self.create_embeds()

    # async def get_week(self):
    #     async with aiohttp.request('get', 'https://alttprleague.com/api/week') as req:
    #         week_response = await req.json()

    #     try:
    #         self.week_data = week_response.get('weeks', [])[0]
    #     except IndexError:
    #         logging.exception("No active league week!")
    #         await self.rtgg_handler.send_message("No active League Week!  This should not have happened.  Contact a league admin/mod for help.")

    async def roll(self):
        if self.tournament_game.preset is None:
            raise Exception('Missing preset.  Please submit!')

        self.seed = await generator.ALTTPRPreset(self.tournament_game.preset).generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off")
        await self.create_embeds()

    async def update_data(self):
        await super().update_data()
        # await self.get_week()

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
            ],
            stream_delay=10
        )

    async def create_race_room(self):
        if self.tournament_game is None or self.tournament_game.preset is None:
            await self.send_race_submission_form(warning=True)
            raise Exception(f"Could not open `{self.episodeid}` because setttings were not submitted.")

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
            team_race=self.tournament_game.game_number == 5,
        )
        return self.rtgg_handler

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
            logging.info(f"Sending tournament submit reminder to {name}.")
            await player.send(msg)

        await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'event': self.event_slug, 'submitted': 1})

    @property
    def bracket_settings(self):
        if self.tournament_game:
            return self.tournament_game.settings

        return None

    @property
    def submission_form(self):
        return [
            {
                'key': 'game',
                'label': 'Game #',
                'settings': {
                    '1': '1',
                    '2': '2',
                    '3': '3',
                    '4': '4',
                    '5': '5',
                }
            },
            {
                'key': 'preset',
                'label': 'Preset',
                'required_if': {
                    'game': ['3', '4']
                },
                'default': 'default',
                'settings': {
                    'default': 'Game 1, 2, or 5',
                    'invrosia': 'Invrosia',
                    'league_swordless': 'League Swordless',
                    'hard_mc': 'Open Hard MC Shuffle',
                    'hard_enemizer': 'Open Hard Enemizer',
                }
            }
        ]

    async def process_submission_form(self, payload, submitted_by):
        embed = discord.Embed(
            title=f"ALTTPR League - {self.versus}",
            description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
            color=discord.Colour.blue()
        )

        if payload['game'] == '1':
            preset_name = 'casualboots'
        elif payload['game'] == '2':
            preset_name = 'crosskeys'
        elif payload['game'] == '5':
            preset_name = 'retrance'
        else:
            if payload['preset'] == 'default':
                raise Exception('Must choose a preset for games 3 or 4.')
            preset_name = payload['preset']

        embed.add_field(name="Game Number", value=payload['game'], inline=False)
        embed.add_field(name="Preset", value=preset_name, inline=False)

        embed.add_field(name="Submitted by", value=submitted_by, inline=False)

        await models.TournamentGames.update_or_create(
            episode_id=self.episodeid,
            defaults={
                'event': self.event_slug,
                'game_number': payload['game'],
                'preset': preset_name
            }
        )

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
            ],
            stream_delay=10
        )
