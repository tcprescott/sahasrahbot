import logging

from alttprbot import models
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot_discord.bot import discordbot

class SGLCoreTournamentRace(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Beat the game",
            event_slug="sgl21alttpr",
            audit_channel=discordbot.get_channel(774336581808291863),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    @classmethod
    async def construct_race_room(cls, episodeid):
        tournament_race = cls(episodeid=episodeid, rtgg_handler=None)

        await discordbot.wait_until_ready()
        tournament_race.data = await tournament_race.configuration()
        await tournament_race.update_data()

        handler = await tournament_race.create_race_room()

        handler.tournament = tournament_race
        tournament_race.rtgg_handler = handler

        logging.info(handler.data.get('name'))
        await models.TournamentResults.update_or_create(srl_id=handler.data.get('name'), defaults={'episode_id': tournament_race.episodeid, 'event': tournament_race.event_slug, 'spoiler': None})

        await tournament_race.send_player_room_info()
        await tournament_race.send_audit_room_info()

        await tournament_race.send_room_welcome()

        await tournament_race.on_room_creation()

        return handler.data

    async def send_audit_room_info(self):
        await self.data.audit_channel.send(f"{self.event_name} - {self.versus} - Episode {self.episodeid} - <{self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])}>")

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=False,
            unlisted=True,
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
            team_race=self.data.coop,
        )
        return self.rtgg_handler
