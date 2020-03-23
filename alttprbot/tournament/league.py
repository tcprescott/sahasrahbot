import json

import discord

from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import (config, spoiler_races, srl_races,
                                tournament_results)
from alttprbot.exceptions import SahasrahBotException
from alttprbot.util import srl
from alttprbot_discord.bot import discordbot

from ..util import speedgaming

WEEKDATA = {
    '1': {
        'type': 'preset',
        'preset': 'open',
        'friendly_name': 'Week 1 - Open'
    },
    '2': {
        'type': 'preset',
        'preset': 'ambrosia',
        'friendly_name': 'Week 2 - Ambrosia'
    },
    '3': {
        'type': 'preset',
        'preset': 'enemizer',
        'friendly_name': 'Week 3 - Enemizer'
    },
    '4': {
        'type': 'mystery',
        'weightset': 'league',
        'friendly_name': 'Week 4 - Mystery'
    },
    '5': {
        'type': 'preset',
        'preset': 'crosskeys',
        'friendly_name': 'Week 5 - Crosskeys'
    },
    '6': {
        'type': 'spoiler',
        'preset': 'keysanity',
        'studyperiod': 0,
        'friendly_name': 'Week 6 - Piloted Spoiler Keysanity'
    },
    '7': {
        'type': 'preset',
        'preset': 'dungeons',
        'coop': True,
        'friendly_name': 'Week 7 - All Dungeons Co-op Info Share - DO NOT RECORD'
    },
}

class WeekNotFoundException(SahasrahBotException):
    pass

async def league_race(episodeid: int, week=None):
    race = LeagueRace(episodeid, week)
    await race._init()
    return race

class LeagueRace():
    def __init__(self, episodeid: int, week=None):
        self.episodeid = int(episodeid)
        self.week = week

    async def _init(self):
        guild_id = await config.get(0, 'AlttprLeagueServer')
        self.guild = discordbot.get_guild(int(guild_id))

        if self.week is None:
            self.week = await config.get(guild_id, 'AlttprLeagueWeek')

        if self.week not in WEEKDATA:
            raise WeekNotFoundException(f'Week {self.week} was not found!')

        self.episode = await speedgaming.get_episode(self.episodeid)
        self.type = WEEKDATA[self.week]['type']
        self.friendly_name = WEEKDATA[self.week]['friendly_name']
        self.spoiler_log_url = None

        if self.type == 'preset':
            self.preset = WEEKDATA[self.week]['preset']
            self.seed, self.preset_dict = await preset.get_preset(self.preset, nohints=True)
            self.goal_after_start = f"vt8 randomizer - {self.preset_dict.get('goal_name', 'unknown')}"
        elif self.type == 'mystery':
            self.weightset = WEEKDATA[self.week]['weightset']
            self.seed = await mystery.generate_random_game(self.weightset, spoilers="mystery", tournament=True)
            self.goal_after_start = f"vt8 randomizer - mystery {self.weightset}"
        elif self.type == 'spoiler':
            self.preset = WEEKDATA[self.week]['preset']
            self.studyperiod = WEEKDATA[self.week]['studyperiod']
            self.seed, self.preset_dict, self.spoiler_log_url = await spoilers.generate_spoiler_game(WEEKDATA[self.week]['preset'])
            self.goal_after_start = f"vt8 randomizer - spoiler {self.preset_dict.get('goal_name', 'unknown')}"
        else:
            raise SahasrahBotException('Week type not found, something went horribly wrong...')

    def get_player_discords(self):
        player_list = []
        for match in ['match1', 'match2']:
            if self.episode[match] is None:
                continue
            for player in self.episode[match]['players']:
                try:
                    if not player.get('discordId', '') == '':
                        member = self.guild.get_member(int(player['discordId']))
                    else:
                        member = self.guild.get_member_named(player['discordTag'])
                    
                    if member is None:
                        raise SahasrahBotException(f"Unable to resolve Discord User for {player['displayName']} ({player['discordTag']}).  Please contact a moderator for help.")
                    player_list.append(member)
                except discord.HTTPException:
                    pass

        return player_list

    def get_player_names(self):
        player_list = []
        for match in ['match1', 'match2']:
            if self.episode[match] is None:
                continue
            for player in self.episode[match]['players']:
                player_list.append(player['displayName'])

        return player_list


async def process_league_race(target, args, client):
    srl_id = srl.srl_race_id(target)
    srl_race = await srl.get_race(srl_id)

    if not srl_race['game']['abbrev'] == 'alttphacks':
        await client.message(target, "This must be an alttphacks race.")
        return

    await client.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
    race = await srl_races.get_srl_race_by_id(srl_id)

    if race:
        await client.message(target, "There is already a game generated for this room.  To cancel it, use the $cancel command.")
        return

    generated_league_race = await league_race(episodeid=args.episodeid, week=args.week)
    player_names = generated_league_race.get_player_names()
    player_discords = generated_league_race.get_player_discords()
    goal = f"ALTTPR League - {', '.join(player_names)} - {generated_league_race.friendly_name}"
    await client.message(target, f".setgoal {goal}")

    embed = await generated_league_race.seed.embed(
        name=goal,
        emojis=discordbot.emojis
    )

    tournament_embed = await generated_league_race.seed.tournament_embed(
        name=goal,
        notes="The permalink for this seed was sent via direct message to each runner.",
        emojis=discordbot.emojis
    )


    broadcast_channels = [a['name'] for a in generated_league_race.episode['channels'] if not a['name'] == 'No Stream']

    if len(broadcast_channels) > 0:
        tournament_embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
        embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)

    audit_channel_id = await config.get(generated_league_race.guild.id, 'AlttprLeagueAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(embed=embed)

    commentary_channel_id = await config.get(generated_league_race.guild.id, 'AlttprLeagueCommentaryChannel')
    if commentary_channel_id is not None and len(broadcast_channels) > 0:
        commentary_channel = discordbot.get_channel(int(commentary_channel_id))
        await commentary_channel.send(embed=tournament_embed)

    for player in player_discords:
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}")

    if generated_league_race.type == 'spoiler':
        await spoiler_races.insert_spoiler_race(srl_id, generated_league_race.spoiler_log_url, generated_league_race.studyperiod)


    await srl_races.insert_srl_race(srl_id, generated_league_race.goal_after_start)
    await tournament_results.insert_tournament_race(
        srl_id=srl_id,
        episode_id=generated_league_race.episodeid,
        permalink=generated_league_race.seed.url,
        event='alttprleague',
        week=generated_league_race.week,
        spoiler=generated_league_race.spoiler_log_url if generated_league_race.spoiler_log_url else None
    )

    await client.message(target, "Seed has been generated, you should have received a DM in Discord.  Please contact a League Moderator if you haven't received the DM.")

async def process_league_race_finish(target, client):
    srl_id = srl.srl_race_id(target)
    srl_race = await srl.get_race(srl_id)

    await tournament_results.record_tournament_results(
        srl_id=srl_id,
        results_json=json.dumps(srl_race['entrants'])
    )
