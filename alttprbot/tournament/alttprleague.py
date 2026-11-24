import logging

import aiohttp

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.alttprgen import spoilers
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament import event_settings


class ALTTPRLeague(ALTTPRTournamentRace):
    settings_data: models.TournamentGames = None

    async def roll(self):
        if self.league_data.get('spoiler', False):
            spoiler = await spoilers.generate_spoiler_game(self.league_data['preset'])
            self.seed = spoiler.seed
            await self.rtgg_handler.schedule_spoiler_race(spoiler.spoiler_log_url, 0)
        else:
            self.seed = await generator.ALTTPRPreset(self.league_data['preset']).generate(allow_quickswap=True,
                                                                                          tournament=True, hints=False,
                                                                                          spoilers="off")

        await self.create_embeds()

    async def get_league_data(self):
        async with aiohttp.request('get', 'https://alttprleague.com/api/episode', params={'id': self.episodeid}) as req:
            league_response = await req.json()

        try:
            self.league_data = league_response['mode']
        except KeyError:
            logging.exception("No active league mode!")
            await self.rtgg_handler.send_message(
                "No active League mode!  This should not have happened.  Contact a league admin/mod for help.")

    async def update_data(self, update_episode=True):
        await super().update_data(update_episode=update_episode)
        await self.get_league_data()

    async def configuration(self):
        return event_settings.tournament_config("invleague")

    async def create_race_room(self):
        goal_type = 'Co-op' if self.league_data['coop'] or self.league_data['spoiler'] else 'Solo'
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=f"Beat the game - Tournament ({goal_type})",
            invitational=True,
            unlisted=False,
            info_user=self.race_info,
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
            team_race=self.league_data['coop'],
            require_even_teams=True,
        )
        return self.rtgg_handler

    # async def send_race_submission_form(self, warning=False):
    #     if self.bracket_settings is not None and not warning:
    #         return

    #     if self.tournament_game and self.tournament_game.submitted and not warning:
    #         return

    #     if warning:
    #         msg = (
    #             f"Your upcoming race room cannot be created because settings have not submitted: `{self.versus}`!\n\n"
    #             f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
    #         )
    #     else:
    #         msg = (
    #             f"Greetings!  Do not forget to submit settings for your upcoming race: `{self.versus}`!\n\n"
    #             f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
    #         )

    #     for name, player in self.player_discords:
    #         if player is None:
    #             continue
    #         logging.info(f"Sending tournament submit reminder to {name}.")
    #         await player.send(msg)

    #     await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'event': self.event_slug, 'submitted': 1})


class ALTTPROpenLeague(ALTTPRLeague):
    async def configuration(self):
        return event_settings.tournament_config("alttprleague")
