from alttprbot import models
from alttprbot.alttprgen import spoilers
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot

from racetime_bot import msg_actions


class ALTTPRSGLive(ALTTPRTournamentRace):
    settings_data: models.TournamentGames = None

    async def roll(self):
        spoiler = await spoilers.generate_spoiler_game('open')
        self.seed = spoiler.seed
        await self.rtgg_handler.schedule_spoiler_race(spoiler.spoiler_log_url, 900)

    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game - Tournament (Solo)',
            event_slug='sgl24alttpr',
            audit_channel=discordbot.get_channel(772351829022474260),
            helper_roles=[
                guild.get_role(590804526114668544),
                guild.get_role(859868643613474816),
                guild.get_role(769544464502226945),
                guild.get_role(1256518642015932491),
            ],
            create_scheduled_events=True,
            room_open_time=30,
            stream_delay=15,
        )

    async def update_data(self, update_episode=True):
        await super().update_data(update_episode)
        self.qualifier = self.friendly_name.lower().startswith('qualifier')

    async def process_tournament_race(self, args, message):
        await self.rtgg_handler.send_message(
            "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        await self.update_data()

        if not self.qualifier:
            await super().process_tournament_race(args, message)
            return

        authorized = await self.can_gatekeep(message['user']['id'])
        if not authorized:
            await self.rtgg_handler.send_message(
                "Only an admin of this tournament or SGL Staff may invoke !tournamentrace.  Please contact Synack for further help.")
            return

        # lock the room
        await self.rtgg_handler.set_invitational()
        await self.rtgg_handler.edit(streaming_required=False)
        await self.rtgg_handler.send_message("This room is now locked.  Late entries are not permitted.")

        await self.roll()
        await self.create_embeds()

        await self.send_audit_message(embed=self.embed)
        await self.send_commentary_message(self.tournament_embed)

        tournamentresults, _ = await models.TournamentResults.update_or_create(
            srl_id=self.rtgg_handler.data.get('name'),
            defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': self.seed.spoiler_log_url})
        tournamentresults.permalink = self.seed.url
        await tournamentresults.save()

        await self.rtgg_handler.set_bot_raceinfo(f"{self.seed.url} - {self.seed_code}")
        await self.rtgg_handler.send_message(f"Seed: {self.seed.url} - {self.seed_code}")

        self.rtgg_handler.seed_rolled = True

    async def send_room_welcome(self):
        if not self.qualifier:
            await super().send_room_welcome()
            return

        await self.rtgg_handler.send_message(
            'Welcome! A tournament admin will roll the seed about 10 minutes before the start time. Room will be locked at that time.',
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

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal="Beat the game - Tournament (Solo)",
            invitational=not self.qualifier,
            unlisted=False,
            info_user=self.race_info,
            start_delay=30 if self.qualifier else 15,
            time_limit=24,
            streaming_required=True,
            auto_start=not self.qualifier,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=not self.qualifier,
            allow_midrace_chat=not self.qualifier,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=False,
            require_even_teams=False,
        )
        return self.rtgg_handler
