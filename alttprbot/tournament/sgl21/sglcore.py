import logging

import discord
from alttprbot import models
from alttprbot.tournament.core import TournamentConfig, TournamentRace, UnableToLookupUserException
from alttprbot_discord.bot import discordbot


class SGLTournamentPlayer(object):
    def __init__(self):
        self.discord_user: discord.Member = None

    @classmethod
    async def construct(cls, discord_id: int, guild: discord.Guild):
        playerobj = cls()

        playerobj.discord_user = guild.get_member(int(discord_id))

        return playerobj

    @classmethod
    async def construct_discord_name(cls, discord_name: str, guild: discord.Guild):
        playerobj = cls()

        playerobj.discord_user = guild.get_member_named(discord_name)
        if playerobj.discord_user is None:
            raise UnableToLookupUserException(f"Unable to lookup player {discord_name}")

        return playerobj

    @property
    def rtgg_id(self):
        return None

    @property
    def twitch_name(self):
        return None

    @property
    def name(self):
        return self.discord_user.name


class SGLCoreTournamentRace(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Beat the game",
            event_slug="sgl21alttpr",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    async def make_tournament_player(self, player):
        if not player['discordId'] == "":
            looked_up_player = await SGLTournamentPlayer.construct(discord_id=player['discordId'], guild=self.guild)
        else:
            looked_up_player = None

        # then, if that doesn't work, try their discord tag kept by SG
        if looked_up_player is None and not player['discordTag'] == '':
            looked_up_player = await SGLTournamentPlayer.construct_discord_name(discord_name=player['discordTag'], guild=self.guild)

        # and failing all that, bomb
        if looked_up_player is None:
            raise UnableToLookupUserException(
                f"Unable to lookup the player `{player['displayName']}`.  Please contact a Tournament moderator for assistance.")

        return looked_up_player

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
        await tournament_race.send_commentator_room_info()
        await tournament_race.send_audit_room_info()

        await tournament_race.send_room_welcome()

        await tournament_race.on_room_creation()

        return handler.data

    @property
    def race_room_log_channel(self):
        return discordbot.get_channel(774336581808291863)

    @property
    def player_racetime_ids(self):
        return []

    async def send_commentator_room_info(self):
        embed = discord.Embed(
            title=f"RT.gg Room Opened - {self.versus}",
            description=f"Greetings!  A RaceTime.gg race room has been automatically opened for an upcoming race that you are commentating.\nYou may access it at {self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])}\n\nEnjoy!",
            color=discord.Colour.blue(),
            timestamp=discord.utils.utcnow()
        )

        for commentator in self.episode['commentators']:
            if not commentator.get('approved', False):
                continue

            try:
                member = self.data.guild.get_member_named(commentator['discordTag'])
                if member is None:
                    continue
                await member.send(embed=embed)
            except discord.HTTPException:
                logging.exception(f"Unable to send DM to {commentator['discordTag']}")
                continue

    async def send_audit_room_info(self):
        await self.race_room_log_channel.send(f"Room created: {self.event_name} - {self.versus} - Episode {self.episodeid} - <{self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])}>")

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


class SGLRandomizerTournamentRace(SGLCoreTournamentRace):
    async def roll(self):
        pass

    async def process_tournament_race(self):
        await self.rtgg_handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        # await self.update_data()
        await self.roll()

        await self.rtgg_handler.set_raceinfo(self.race_info_rolled, overwrite=True)
        await self.rtgg_handler.send_message(self.seed_info)

        await self.send_audit_message(message=f"<{self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])}> - {self.event_name} - {self.versus} - Episode {self.episodeid} - {self.seed_info}")

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})
        tournamentresults.permalink = self.seed_info
        await tournamentresults.save()

        await self.rtgg_handler.send_message("Seed has been generated!  GLHF")
        self.rtgg_handler.seed_rolled = True

    async def send_room_welcome(self):
        await self.rtgg_handler.send_message('Welcome. Use !tournamentrace (without any arguments) to roll your seed!  You do NOT need to wait for your setup helper to do this or start your race, they will appear later to setup the stream.')

    @property
    def seed_info(self):
        return ""

    @property
    def race_info_rolled(self):
        info = f"{self.seed_info} - {self.event_name} - {self.versus} - {self.friendly_name}"
        if self.broadcast_channels:
            info += f" - Restream(s) at {', '.join(self.broadcast_channels)}"
        info += f" - {self.episodeid}"
        return info
