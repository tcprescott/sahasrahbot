import datetime
import os
import logging
import json

import aiohttp
import discord
from pytz import timezone
from pyz3r.mystery import get_random_option

from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import (config, spoiler_races, tournament_results,
                                twitch_command_text, srlnick, league_playoffs)
from alttprbot.util import speedgaming
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord
from alttprbot_racetime import bot as racetime

tz = timezone('US/Eastern')

WEEKDATA = {
    '1': {
        'type': 'preset',
        'preset': 'dungeons',
        'coop': True,
        'friendly_name': 'Week 1 - All Dungeons Co-op Info Share'
    },
    '2': {
        'type': 'preset',
        'preset': 'open',
        'friendly_name': 'Week 2 - Open'
    },
    '3': {
        'type': 'preset',
        'preset': 'casualboots',
        'friendly_name': 'Week 3 - Casual Boots'
    },
    '4': {
        'type': 'spoiler',
        'preset': 'keysanity',
        'studyperiod': 0,
        'friendly_name': 'Week 4 - Piloted Spoiler Keysanity'
    },
    '5': {
        'type': 'mystery',
        'weightset': 'league',
        'friendly_name': 'Week 5 - Mystery'
    },
    '6': {
        'type': 'preset',
        'preset': 'adkeys',
        'friendly_name': 'Week 6 - All Dungeons Keysanity'
    },
    '7': {
        'type': 'preset',
        'preset': 'enemizer',
        'coop': True,
        'friendly_name': 'Week 7 - Enemizer Co-op Info Share'
    }
}

PLAYOFFDATA = {
    1: {
        'type': 'preset',
        'preset': 'open',
        'friendly_name': 'Playoffs Game 1 - Open'
    },
    2: {
        'type': 'preset',
        'preset': 'casualboots',
        'friendly_name': 'Playoffs Game 2 - Standard w/ Sword and Boots'
    },
    3: {
        'type': 'database',
        'friendly_name': 'Playoffs Game 3'
    },
    4: {
        'type': 'database',
        'friendly_name': 'Playoffs Game 4'
    },
    5: {
        'type': 'database',
        'friendly_name': 'Playoffs Game 5'
    }
}

SETTINGSMAP = {
    'Standard': 'standard',
    'Maps/Compasses': 'mc',
    'Maps/Compasses/Small Keys': 'mcs',
    'Keysanity': 'full',
    'Defeat Ganon': 'ganon',
    'Fast Ganon': 'fast_ganon',
    'All Dungeons': 'dungeons',
    'Open': 'open',
    'Inverted': 'inverted',
    'Randomized': 'randomized',
    'Assured': 'assured',
    'Vanilla': 'vanilla',
    'Swordless': 'swordless',
    'Hard': 'hard',
    'Normal': 'normal',
    'Off': 'off',
    'Enemy Shuffle': 'enemies',
    'Boss Shuffle': 'bosses',
    'Enemies and Bosses': 'full_enemizer',
    'Random': 'random',
}


class WeekNotFoundException(SahasrahBotException):
    pass


class SettingsSubmissionNotFoundException(SahasrahBotException):
    pass


class UnableToLookupUserException(SahasrahBotException):
    pass


class LeaguePlayer():
    def __init__(self):
        pass

    @classmethod
    async def construct(cls, name, guild, name_type='twitch'):
        playerobj = cls()

        name_type_map = {
            'twitch': 'twitch',
            'discord': 'discord',
            'display_name': 'discord',
            'discord_id': 'discord_id',
            'rtgg': 'rtgg_name',
            'rtgg_id': 'rtgg_id',
        }

        name = name.strip()
        if name_type == "discord_id":
            name = int(name)

        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/player/',
            params={
                name_type_map[name_type]: name,
            },
            raise_for_status=True
        ) as resp:
            r = await resp.json()
            players = r['results']

        if players is None:
            return None

        if name_type == 'twitch':
            player = [p for p in players if p['twitch_name'].lower()
                      == name.lower()][0]
        elif name_type == 'discord':
            player = [p for p in players if p['discord'] == name][0]
        elif name_type == 'display_name':
            player = players[0]
        elif name_type == 'discord_id':
            player = [p for p in players if p['discord_id'] == name][0]
        elif name_type == 'rtgg':
            player = [p for p in players if p['rtgg_name'] == name][0]
        else:
            raise Exception('Invalid name type.')

        playerobj.data = player

        if player.get('discord_id', None) is None:
            playerobj.discord_user = guild.get_member_named(player['discord'])
        else:
            playerobj.discord_user = guild.get_member(player['discord_id'])

        return playerobj


class LeagueRace():
    def __init__(self, episodeid: int, week=None, create_seed=True):
        self.episodeid = int(episodeid)
        self.week = week
        self.create_seed = create_seed
        self.players = []

    @classmethod
    async def construct(cls, episodeid, week=None, create_seed=True):
        league_race = cls(episodeid, week, create_seed)
        guild_id = await config.get(0, 'AlttprLeagueServer')
        league_race.guild = discordbot.get_guild(int(guild_id))

        if league_race.week is None:
            league_race.week = await config.get(guild_id, 'AlttprLeagueWeek')

        if league_race.week not in WEEKDATA and not league_race.week == 'playoffs':
            raise WeekNotFoundException(
                f'Week {league_race.week} was not found!')

        league_race.episode = await speedgaming.get_episode(league_race.episodeid)

        if league_race.episode['event'].get('slug') not in ['invleague', 'alttprleague']:
            raise Exception('SG Episode ID not for ALTTPR League Race')

        for player in league_race.episode['match1']['players']:
            # first try a more concrete match of using the discord id cached by SG
            looked_up_player = await league_race.make_league_player_from_sg(player)
            league_race.players.append(looked_up_player)

        if league_race.is_playoff:
            league_race.playoff_settings = await league_playoffs.get_playoff_by_episodeid_submitted(league_race.episodeid)
            if league_race.playoff_settings:
                league_race.week = 'playoffs'

        if league_race.create_seed:
            if league_race.is_playoff:
                await league_race._roll_playoffs()
            else:
                await league_race._roll_general()

        return league_race

    async def make_league_player_from_sg(self, player):
        try:
            looked_up_player = await LeaguePlayer.construct(name=player['discordId'], guild=self.guild, name_type='discord_id')
        except ValueError:
            looked_up_player = None

        # then, if that doesn't work, try their discord tag kept by SG
        if looked_up_player is None and not player['discordTag'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['discordTag'], guild=self.guild, name_type='discord')

        # then, if that doesn't work, try their streamingFrom name
        if looked_up_player is None and not player['streamingFrom'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['streamingFrom'], guild=self.guild, name_type='twitch')

        # finally, try publicStream
        if looked_up_player is None and not player['publicStream'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['publicStream'], guild=self.guild, name_type='twitch')

        # a final hail mary pass
        if looked_up_player is None and not player['displayName'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['displayName'], guild=self.guild, name_type='display_name')

        # and failing all that, bomb
        if looked_up_player is None:
            raise UnableToLookupUserException(
                f"Unable to lookup the player `{player['displayName']}`.  Please contact a league moderator for assistance.")

        return looked_up_player

    async def _roll_playoffs(self):
        if self.playoff_settings is None:
            raise Exception('Missing playoff settings.  Please submit!')

        if self.gen_type == 'preset':
            self.preset = self.playoff_settings['preset']
            self.seed, self.preset_dict = await preset.get_preset(self.preset, nohints=True, allow_quickswap=True)
        elif self.gen_type == 'database':
            self.preset = None
            self.preset_dict = None
            self.seed = await alttpr_discord.ALTTPRDiscord.generate(
                settings=json.loads(self.playoff_settings['settings'])
            )

    async def _roll_general(self):
        self.spoiler_log_url = None

        if self.gen_type == 'preset':
            self.preset = WEEKDATA[self.week]['preset']
            self.seed, self.preset_dict = await preset.get_preset(self.preset, nohints=True, allow_quickswap=True)
        elif self.gen_type == 'mystery':
            self.weightset = WEEKDATA[self.week]['weightset']
            self.seed = await mystery.generate_random_game(weightset=self.weightset, spoilers="mystery", tournament=True)
        elif self.gen_type == 'spoiler':
            self.preset = WEEKDATA[self.week]['preset']
            self.studyperiod = WEEKDATA[self.week]['studyperiod']
            self.seed, self.preset_dict, self.spoiler_log_url = await spoilers.generate_spoiler_game(WEEKDATA[self.week]['preset'])
        else:
            raise SahasrahBotException(
                'Week type not found, something went horribly wrong...')

    @property
    def is_playoff(self):
        return self.week == 'playoffs'

    @property
    def friendly_name(self):
        if self.is_playoff and self.playoff_settings is not None:
            return PLAYOFFDATA[self.playoff_settings['game_number']]['friendly_name']

        return WEEKDATA[self.week]['friendly_name']

    @property
    def gen_type(self):
        if self.is_playoff and self.playoff_settings is not None:
            return self.playoff_settings['type']

        return WEEKDATA[self.week]['type']

    @property
    def coop(self):
        if self.week == 'playoffs':
            return False

        return WEEKDATA[self.week].get('coop', False)

    @property
    def versus(self):
        t = []
        for team in self.players_by_team:
            t.append(' and '.join([p.data['name']
                                   for p in self.players_by_team[team]]))

        return ' vs. '.join(t)

    @property
    def versus_and_team(self):
        t = []
        for team in self.players_by_team:
            t.append(
                f"{' and '.join([p.data['name']for p in self.players_by_team[team]])} ({team})")

        return ' vs. '.join(t)

    @property
    def team_versus(self):
        return ' vs. '.join(self.team_names)

    @property
    def player_discords(self):
        return [(p.data['name'], p.discord_user) for p in self.players]

    @property
    def player_names(self):
        return [p.data['name'] for p in self.players]

    @property
    def team_names(self):
        return list(set([p.data['team_name'] for p in self.players]))

    @property
    def division_names(self):
        return list(set([p.data['division_name'] for p in self.players]))

    @property
    def division_urls(self):
        return list(set([p.data['division_url'] for p in self.players]))

    @property
    def players_by_team(self):
        result = {}
        for team in self.team_names:
            result[team] = [
                p for p in self.players if p.data['team_name'] == team]
        return result

    @property
    def twitch_mode_command(self):
        if self.is_playoff and self.playoff_settings:
            if self.playoff_settings['game_number'] == 1:
                mode = "open"
            elif self.playoff_settings['game_number'] == 2:
                mode = "standard w/ sword and boots"
            else:
                mode = self.seed.generated_goal

            return f"The settings for this race is \"{mode}\"!  It is game number {self.playoff_settings['game_number']} of this series."

        if self.gen_type == 'preset':
            return f"The preset for this race is {self.preset}."

        if self.gen_type == 'spoiler':
            return f"This is a {self.preset} spoiler race."

        if self.gen_type == 'mystery':
            return f"The weightset for this race is {self.weightset}."

    @property
    def broadcast_channels(self):
        return [a['name'] for a in self.episode['channels'] if not " " in a['name']]

    @property
    def submit_link(self):
        return f"https://docs.google.com/forms/d/e/1FAIpQLSdwgiOdeDEUUv7S_ZmuJdsV7rYG9LiyvSqQvPZetJByQ6k4XQ/viewform?usp=pp_url&entry.521975083={self.episodeid}"


async def process_league_race(handler, episodeid=None, week=None):
    await handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

    race = await tournament_results.get_active_tournament_race(handler.data.get('name'))
    if race:
        episodeid = race.get('episode_id')
    if race is None and episodeid is None:
        await handler.send_message("Please provide an SG episode ID.")
        return

    try:
        league_race = await LeagueRace.construct(episodeid=episodeid, week=week)
    except Exception as e:
        logging.exception("Problem creating league race.")
        await handler.send_message(f"Could not process league race: {str(e)}")
        return

    if league_race.is_playoff:
        if league_race.playoff_settings is None:
            await handler.send_message("A form has not been submitted for this race.  Please do that.")
            return

    teams = league_race.players_by_team

    t = []
    for team in teams:
        t.append(' and '.join([p.data['name'] for p in teams[team]]))

    goal = f"ALTTPR League - {league_race.versus_and_team} - {league_race.friendly_name}"

    embed = await league_race.seed.embed(
        name=goal,
        notes=league_race.team_versus,
        emojis=discordbot.emojis
    )

    tournament_embed = await league_race.seed.tournament_embed(
        name=goal,
        notes=league_race.team_versus,
        emojis=discordbot.emojis
    )

    goal += f" - ({'/'.join(league_race.seed.code)})"

    tournament_embed.insert_field_at(
        0, name='RaceTime.gg', value=handler.bot.http_uri(handler.data['url']), inline=False)
    embed.insert_field_at(
        0, name='RaceTime.gg', value=handler.bot.http_uri(handler.data['url']), inline=False)

    if broadcast_channels := league_race.broadcast_channels:
        twitch_mode_text = league_race.twitch_mode_command
        twitch_teams_text = f"This race is between {league_race.team_versus}.  Check out rankings for division(s) {', '.join(league_race.division_names)} at {' '.join(league_race.division_urls)}"

        for channel in broadcast_channels:
            await twitch_command_text.insert_command_text(channel.lower(), "mode", twitch_mode_text)
            await twitch_command_text.insert_command_text(channel.lower(), "teams", twitch_teams_text)

        tournament_embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
        embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)

        goal += f" - Restream(s) at {', '.join(broadcast_channels)}"

    await handler.set_raceinfo(goal, overwrite=True)

    audit_channel_id = await config.get(league_race.guild.id, 'AlttprLeagueAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(embed=embed)
    else:
        audit_channel = None

    commentary_channel_id = await config.get(
        guild_id=league_race.guild.id,
        parameter='AlttprLeagueCommentaryChannel' if league_race.episode['event'].get(
            'slug', 'invleague') == 'invleague' else 'AlttprLeagueOpenCommChannel'
    )
    commentary_channel = discordbot.get_channel(int(commentary_channel_id))
    if commentary_channel and len(broadcast_channels) > 0:
        await commentary_channel.send(embed=tournament_embed)

    for name, player in league_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True))
            await handler.send_message(f"Could not send DM to {name}.  Please contact a League Moderator for assistance.")
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True))
                await handler.send_message(f"Could not send DM to {player.name}#{player.discriminator}.  Please contact a League Moderator for assistance.")

    if league_race.gen_type == 'spoiler':
        await spoiler_races.insert_spoiler_race(handler.data.get('name'), league_race.spoiler_log_url, league_race.studyperiod)
        await handler.send_message("The spoiler log will be posted in chat at the start of the race.  ENSURE YOUR PILOT IS WATCHING THE CHAT.")

    if race is None:
        await tournament_results.insert_tournament_race(
            srl_id=handler.data.get('name'),
            episode_id=league_race.episodeid,
            permalink=league_race.seed.url,
            event='alttprleague_s3',
            week=league_race.week,
            spoiler=league_race.spoiler_log_url if league_race.spoiler_log_url else None
        )
    else:
        await tournament_results.update_tournament_results_rolled(
            srl_id=handler.data.get('name'),
            permalink=league_race.seed.url,
            week=league_race.week,
        )

    await handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a League Moderator if you haven't received the DM.")
    handler.seed_rolled = True


async def process_league_race_start(handler):
    race_id = handler.data.get('name')

    if race_id is None:
        return

    race = await tournament_results.get_active_tournament_race(race_id)

    if race is None:
        return

    # if os.environ.get("LEAGUE_SUBMIT_GAME_SECRET"):
    #     async with aiohttp.request(
    #         method='get',
    #         url='https://alttprleague.com/json_ep/submit-game',
    #         params={
    #             'slug': race_id,
    #             'sgl': race['episode_id'],
    #             'secret': os.environ.get("LEAGUE_SUBMIT_GAME_SECRET")
    #         }
    #     ) as _:
    #         pass
    # else:
    #     logging.info(
    #         f"Would have reported match {race_id} for episode {race['episode_id']}")

    await tournament_results.update_tournament_results(race_id, status="STARTED")


async def create_league_race_room(episodeid):
    rtgg_alttpr = racetime.racetime_bots['alttpr']
    race = await tournament_results.get_active_tournament_race_by_episodeid(episodeid)
    if race:
        async with aiohttp.request(
                method='get',
                url=rtgg_alttpr.http_uri(f"/{race['srl_id']}/data"),
                raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await tournament_results.delete_active_tournament_race(race['srl_id'])

    league_race = await LeagueRace.construct(episodeid=episodeid, create_seed=False)

    if league_race.coop:
        handler = await rtgg_alttpr.startrace(
            custom_goal='Co-op Info Share',
            invitational=True,
            unlisted=True,
            info=f"ALTTPR League - {league_race.versus_and_team}",
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0
        )
    else:
        handler = await rtgg_alttpr.startrace(
            goal="Beat the game",
            invitational=True,
            unlisted=True,
            info=f"ALTTPR League - {league_race.versus_and_team}",
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0
        )

    logging.info(handler.data.get('name'))
    await tournament_results.insert_tournament_race(
        srl_id=handler.data.get('name'),
        episode_id=league_race.episodeid,
        event='alttprleague_s3'
    )

    for rtggid in [p.data['rtgg_id'] for p in league_race.players]:
        await handler.invite_user(rtggid)

    embed = discord.Embed(
        title=f"RT.gg Room Opened - {league_race.versus_and_team}",
        description=f"Greetings!  A RaceTime.gg race room has been automatically opened for you.\nYou may access it at {handler.bot.http_uri(handler.data['url'])}\n\nEnjoy!",
        color=discord.Colour.blue(),
        timestamp=datetime.datetime.now()
    )

    if league_race.is_playoff:
        if league_race.playoff_settings is None:
            await handler.send_message("WARNING: A form has not been submitted for this race.  Please check your DMs for details.")
            embed.add_field(name='WARNING: Missing settings submission!', value=f"Fill this form out as soon as possible <{league_race.submit_link}>.")

    for name, player in league_race.player_discords:
        if player is None:
            logging.info(f'Could not DM {name}')
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            logging.info(f'Could not send room opening DM to {name}')
            continue

    if os.environ.get("LEAGUE_SUBMIT_GAME_SECRET"):
        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/submit-game/',
            params={
                'slug': handler.data.get('name'),
                'sg': episodeid,
                'secret': os.environ.get("LEAGUE_SUBMIT_GAME_SECRET")
            }
        ) as _:
            pass
    else:
        logging.info(
            f"Would have reported match {handler.data.get('name')} for episode {episodeid}")

    await handler.send_message('Welcome. Use !leaguerace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of you race.  If you need help, ping @Mods in the ALTTPR League Discord.')
    await handler.edit(unlisted=False)

    return handler.data


async def process_playoff_form(form):
    episode_id = int(form['SpeedGaming Episode ID'])
    playoff_round = form['Playoff Round']
    game_number = int(form['Game Number'])

    existing_playoff_race = await league_playoffs.get_playoff_by_episodeid_submitted(episode_id)
    if existing_playoff_race:
        return

    league_race = await LeagueRace.construct(episodeid=episode_id, week='playoffs', create_seed=False)

    if PLAYOFFDATA[game_number].get('type') == 'preset':
        embed = discord.Embed(
            title=f"ALTTPR League Playoffs - {playoff_round} - Game #{game_number} - {league_race.versus_and_team}",
            description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a league moderator.',
            color=discord.Colour.blue()
        )
        embed.add_field(name='Preset', value=PLAYOFFDATA[game_number].get('preset'), inline=False)

        logging.info(f"{game_number=}")
        await league_playoffs.insert_playoff(episode_id=episode_id, playoff_round=playoff_round, game_number=game_number, gen_type='preset', preset=PLAYOFFDATA[game_number].get('preset'))

    elif PLAYOFFDATA[game_number].get('type') == 'database':
        randomized_fields = []

        if (goal := SETTINGSMAP[form.get('Goal', 'Random')]) == 'random':
            randomized_fields.append('Goal')
            goal = get_random_option(
                {
                    'dungeons': 1,
                    'ganon': 1,
                    'fast_ganon': 1
                }
            )

        if (world_state := SETTINGSMAP[form.get('World State', 'Random')]) == 'random':
            randomized_fields.append('World State')
            world_state = get_random_option(
                {
                    'open': 1,
                    'standard': 1,
                    'inverted': 1
                }
            )

        if (swords := SETTINGSMAP[form.get('Swords', 'Random')]) == 'random':
            randomized_fields.append('Swords')
            swords = get_random_option(
                {
                    'assured': 1,
                    'randomized': 1,
                    'vanilla': 1,
                    'swordless': 1
                }
            )

        if (enemizer := SETTINGSMAP[form.get('Enemizer', 'Random')]) == 'random':
            randomized_fields.append('Enemizer')
            enemizer = get_random_option(
                {
                    'off': 40,
                    'enemies': 20,
                    'bosses': 20,
                    'full_enemizer': 20
                }
            )

        if (dungeon_items := SETTINGSMAP[form.get('Dungeon Item Shuffle', 'Random')]) == 'random':
            randomized_fields.append('Dungeon Item Shuffle')
            dungeon_items = get_random_option(
                {
                    'standard': 40,
                    'mc': 20,
                    'mcs': 20,
                    'full': 20
                }
            )

        if (item_pool := SETTINGSMAP[form.get('Item Pool', 'Random')]) == 'random':
            randomized_fields.append('Item Pool')
            item_pool = get_random_option(
                {
                    'normal': 1,
                    'hard': 1
                }
            )

        if enemizer in ['enemies', 'full_enemizer'] and world_state == 'standard' and swords in ['swordless', 'randomized']:
            logging.warning(f"Processing settings conflict for {episode_id}.")
            if form.get('World State', 'Random') == 'Random':
                world_state = 'open'
            elif form.get('Swords', 'Random') == 'Random':
                swords = 'assured'
            elif form.get('Enemizer', 'Random') == 'Random':
                if enemizer == 'full_enemizer':
                    enemizer = 'bosses'
                else:
                    enemizer = 'off'
            else:
                logging.warning(f"Detected standard enemizer submission for {episode_id}, not fixing this because it was specifically chosen.")

        if not len(randomized_fields) in [0, 3]:
            embed = discord.Embed(
                title=f"ERROR SETTINGS NOT RECORDED - {playoff_round} - Game #{game_number} - {league_race.versus_and_team}",
                description='Error, your settings were not recorded!',
                color=discord.Colour.red()
            )
            if randomized_fields:
                embed.add_field(name="Error!", value=f"Need three settings randomized, but had {', '.join(randomized_fields)}", inline=False)
            else:
                embed.add_field(name="Error!", value="No settings were chosen for randomization.  Please resubmit.", inline=False)
        else:
            embed = discord.Embed(
                title=f"ALTTPR League Playoffs - {playoff_round} - Game #{game_number} - {league_race.versus_and_team}",
                description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a league moderator.',
                color=discord.Colour.blue()
            )
            if len(randomized_fields) == 0:
                embed.add_field(name="WARNING", value='No options were randomized by your opponent.', inline=False)
            else:
                embed.add_field(name="Settings that were randomized", value=', '.join(randomized_fields), inline=False)
            embed.add_field(name='Goal', value=goal, inline=True)
            embed.add_field(name='World State', value=world_state, inline=True)
            embed.add_field(name='Swords', value=swords, inline=True)
            embed.add_field(name='Enemizer', value=enemizer, inline=True)
            embed.add_field(name='Dungeon Item Shuffle', value=dungeon_items, inline=True)
            embed.add_field(name='Item Pool', value=item_pool, inline=True)

            settings = {
                "allow_quickswap": True,
                "glitches": "none",
                "item_placement": "advanced",
                "dungeon_items": dungeon_items,
                "accessibility": "items",
                "goal": goal,
                "crystals": {
                    "ganon": '7',
                    "tower": '7',
                },
                "mode": world_state,
                "entrances": "none",
                "hints": "off",
                "weapons": swords,
                "item": {
                    "pool": item_pool,
                    "functionality": "normal"
                },
                "tournament": True,
                "spoilers": "off",
                "lang": "en",
                "enemizer": {
                        "boss_shuffle": "full" if enemizer in ["bosses", "full_enemizer"] else "none",
                        "enemy_shuffle": "shuffled" if enemizer in ["enemies", "full_enemizer"] else "none",
                        "enemy_damage": "default",
                        "enemy_health": "default"
                }
            }

            logging.info(f"{game_number=} {settings=}")

            await league_playoffs.insert_playoff(episode_id=episode_id, playoff_round=playoff_round, game_number=game_number, gen_type='database', settings=settings)
    else:
        raise Exception('Unknown playoff game type.  This should never happen.')

    audit_channel_id = await config.get(league_race.guild.id, 'AlttprLeagueAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(embed=embed)
    else:
        audit_channel = None

    for name, player in league_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)


async def send_race_submission_form(episodeid):
    results = await league_playoffs.get_playoff_by_episodeid(episodeid)
    if results:
        return

    league_race = await LeagueRace.construct(episodeid=episodeid, week='playoffs', create_seed=False)

    msg = (
        f"Greetings!  Do not forget to submit settings for your upcoming race: `{league_race.versus_and_team}`!\n\n"
        f"For your convenience, you visit {league_race.submit_link} to submit the settings for this match after talking to your opponent.\n\n"
        "As a reminder, settings must be submitted for every match, **including games** 1 and 2!"
    )

    for name, player in league_race.player_discords:
        if player is None:
            continue
        logging.info(f"Sending league playoff submit reminder to {name}.")
        await player.send(msg)

    await league_playoffs.insert_playoff(episode_id=episodeid, submitted=0)


async def is_league_race(name):
    race = await tournament_results.get_active_tournament_race(name)
    if race and race['event'] == 'alttprleague_s3':
        return True
    return False


async def can_gatekeep(rtgg_id):
    guild_id = await config.get(0, 'AlttprLeagueServer')
    guild = discordbot.get_guild(int(guild_id))
    nicknames = await srlnick.get_discord_id_by_rtgg(rtgg_id)

    if not nicknames:
        return False

    discord_user = guild.get_member(nicknames[0]['discord_user_id'])

    if not discord_user:
        return False

    if discord.utils.find(lambda m: m.name in ['Admin', 'Mods', 'Restream Mod', 'Crew Mod', 'Reporting Mod', 'SG Mods', 'Bot Overlord', 'Speedgaming', 'Restreamers'], discord_user.roles):
        return True

    return False
