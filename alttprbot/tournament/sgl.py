import datetime
import json
import logging
import random
import string
import asyncio
import os

import aiohttp
import discord
import gspread_asyncio
from slugify import slugify
import isodate

from alttprbot.alttprgen import preset, randomizer
from alttprbot.database import config, sgl2020_tournament, patch_distribution
from alttprbot.util import gsheet, speedgaming
from alttprbot_discord.bot import discordbot
import alttprbot_racetime.bot
from config import Config as c

SMM2_GDRIVE_TEMPLATE = os.environ.get('SGL_SMM2_GDRIVE_TEMPLATE', None)
SMM2_GDRIVE_FOLDER = os.environ.get('SGL_SMM2_GDRIVE_FOLDER', None)
SMM2_SHEET_OWNER = os.environ.get('SGL_SMM2_SHEET_OWNER', None)
SGL_RESULTS_SHEET = os.environ.get('SGL_RESULTS_SHEET', None)

EVENTS = {
    'sglive2020alttpr': {
        "rtgg_goal": 1450,
        "sheet": "alttpr"
    },
    'sglive2020aosr': {
        "rtgg_goal": 1458,
        "sheet": "aosr"
    },
    'sglive2020cv1': {
        "rtgg_goal": 1459,
        "sheet": "cv1"
    },
    'sglive2020ffr': {
        "rtgg_goal": 1452,
        "sheet": "ffr"
    },
    'sglive2020mmx': {
        "rtgg_goal": 1462,
        "sheet": "mmx"
    },
    'sglive2020smz3': {
        "rtgg_goal": 1455,
        "sheet": "smz3"
    },
    'sglive2020smm2': {
        "rtgg_goal": 1460,
        "sheet": "smm2",
        "platform": "discord"
    },
    'sglive2020smo': {
        "rtgg_goal": 1461,
        "sheet": "smo",
    },
    'sgl2020smany': {
        "rtgg_goal": 1453,
        "sheet": "smany",
    },
    'sgl2020smdab': {
        "rtgg_goal": 1454,
        "sheet": "smdab",
    },
    'sglive2020smr': {
        "rtgg_goal": 1456,
        "sheet": "smr",
    },
    'sglive2020z1r': {
        "rtgg_goal": 1457,
        "sheet": "z1r",
    },
    'sglive2020ootr': {
        "rtgg_goal": 1451,
        "sheet": "ootr",
    },
    'sglive2020smb3': {
        "rtgg_goal": 1463,
        "sheet": "smb3",
    },
}


class SpeedGamingUser():
    def __init__(self, guild, player):
        self.display_name = player['displayName']
        self.public_stream = player['publicStream']
        self.streaming_from = player['streamingFrom']
        self.discord_id = player['discordId']
        self.discord_tag = player['discordTag']

        self.discord_user = None

        if not player['discordId'] == '':
            if member := guild.get_member(int(player['discordId'])):
                self.discord_user = member
                return
        else:
            if member := guild.get_member_named(player['discordTag']):
                self.discord_user = member
            elif member := guild.get_member_named(player['displayName']):
                self.discord_user = member


class SGLiveRace():
    @classmethod
    async def construct(cls, episode_id):
        sgl_race = cls()

        guild_id = await config.get(0, 'SpeedGamingLiveGuild')
        sgl_race.guild = discordbot.get_guild(int(guild_id))

        sgl_race.episode_data = await speedgaming.get_episode(episode_id)
        sgl_race.players = []
        for player in sgl_race.episode_data['match1']['players']:
            sgl_race.players.append(SpeedGamingUser(sgl_race.guild, player))

        return sgl_race

    async def create_seed(self):
        method = f'event_{self.event_slug}'
        if hasattr(self, method):
            self.bingo_password = None
            self.seed_id = None
            self.permalink = None
            self.goal_postfix = ""

            await getattr(self, method)()
            return True
        else:
            return False

    # ALTTPR
    async def event_sglive2020alttpr(self):
        self.seed, self.preset_dict = await preset.get_preset('openboots', nohints=True, allow_quickswap=True)

        # Two mandatory values
        self.permalink = self.seed.url
        self.seed_id = self.seed.hash

        self.goal_postfix = f" - {self.permalink} - ({'/'.join(self.seed.code)})"

    # AOSR
    async def event_sglive2020aosr(self):
        self.seed_id, self.permalink = randomizer.roll_aosr(
            logic='AreaTechTeirs', panther='Rand70Dup', boss='Vanilla', weight="3.5", kicker='false', levelexp='Vanilla')
        self.goal_postfix = f" - {self.permalink}"

    # Castlevania 1
    # async def event_sglive2020cv1(self):
    #     pass

    # Final Fantasy Randomizer
    async def event_sglive2020ffr(self):
        self.seed_id, self.permalink = randomizer.roll_ffr(
            flags='yGcifaseK8fJxIkkAzUzYAzx32UoP5toiyJrTE864J9FEyMsXe5XhM5T94nANOh1T6wJN7BZU4p3r3WORe9o7vyXSpZD')
        self.goal_postfix = f" - {self.permalink}"

    # Megaman X
    # async def event_sglive2020mmx(self):
    #     pass

    # SMZ3
    async def event_sglive2020smz3(self):
        self.seed, self.preset_dict = await preset.get_preset('normal', randomizer='smz3')

        # Two mandatory values
        self.permalink = self.seed.url
        self.seed_id = self.seed.slug_id

        self.goal_postfix = f" - {self.permalink} - ({self.seed.code})"

    # Super Mario Maker 2
    # TODO: Copy scoring sheet template, populate spreadsheet w/ appropriate data.
    async def event_sglive2020smm2(self):
        loop = asyncio.get_event_loop()
        copy_workbook = gsheet.drive_service.files().copy(
            fileId=SMM2_GDRIVE_TEMPLATE,
            body={
                'name': f"SMM2 - {self.episode_id} - {self.versus}",
                'parents': [SMM2_GDRIVE_FOLDER]
            }
        )
        results = await loop.run_in_executor(None, copy_workbook.execute)
        self.permalink = f"https://docs.google.com/spreadsheets/d/{results['id']}/edit#gid=0"
        self.seed_id = results['id']

        set_owner = gsheet.drive_service.permissions().create(
            fileId=self.seed_id,
            transferOwnership=True,
            body={
                'type': 'user',
                'role': 'owner',
                'emailAddress': 'tcprescott@gmail.com'
            }
        )
        await loop.run_in_executor(None, set_owner.execute)

        set_anyone = gsheet.drive_service.permissions().create(
            fileId=self.seed_id,
            body={
                'type': 'anyone',
                'role': 'writer',
                'allowFileDiscovery': False
            }
        )
        await loop.run_in_executor(None, set_anyone.execute)

        agcm = gspread_asyncio.AsyncioGspreadClientManager(gsheet.get_creds)
        agc = await agcm.authorize()
        wb = await agc.open_by_key(self.seed_id)
        wks = await wb.get_worksheet(0)

        await wks.batch_update(data=[
            {
                'range': 'B3:B5',
                'values': [[self.players[0].display_name], [self.players[1].display_name], ['']]
            },
            {
                'range': 'E2:G4',
                'values': [['', '', ''], ['', '', ''], ['', '', '']]
            },
            {
                'range': 'E2:G4',
                'values': [['', '', ''], ['', '', ''], ['', '', '']]
            },
            {
                'range': 'B10:B11',
                'values': [[''], ['']]
            },
            {
                'range': 'B14:D15',
                'values': [['', '', ''], ['', '', '']]
            },
            {
                'range': 'B18:D19',
                'values': [['', '', ''], ['', '', '']]
            },
        ], value_input_option="RAW")

    # SMO
    async def event_sglive2020smo(self):
        self.bingo_password = get_random_string(8)
        self.seed_id = await randomizer.create_bingo_room(
            config={
                'room_name': f'SpeedGamingLive 2020 - {self.versus} - {self.episode_id}',
                'passphrase': self.bingo_password,
                'nickname': 'SahasrahBot',
                'game_type': 45,
                'variant_type': 45,
                'custom_json': '',
                'lockout_mode': 1,
                'seed': '',
                'is_spectator': 'on',
                'hide_card': 'on'
            }
        )
        self.permalink = f"https://bingosync.com/room/{self.seed_id}"
        self.goal_postfix = f" - {self.permalink} - Password: {self.bingo_password}"

    # SM Any%
    # async def event_sgl2020smany(self):
    #     pass

    # SM DAB
    # async def event_sgl2020smdab(self):
    #     pass

    # Super Metroid Randomizer
    async def event_sglive2020smr(self):
        result = await patch_distribution.select_random_patch('sgldash')
        await patch_distribution.update_as_used(result['id'])
        self.seed_id = result['patch_id']
        self.permalink = f"https://sgldash.synack.live/?patch={self.seed_id}"
        self.goal_postfix = f" - {self.permalink}"

    # Zelda 1 Randomizer
    async def event_sglive2020z1r(self):
        self.seed_id, flags = randomizer.roll_z1r(
            'VlWlIEwJ1MsKkaOCWhlit2veXNSffs')
        self.permalink = f"Seed: {self.seed_id} - Flags: {flags}"
        self.goal_postfix = f" - {self.permalink}"

    # Ocarina of Time Randomizer
    async def event_sglive2020ootr(self):
        self.seed = await randomizer.roll_ootr(
            encrypt=True,
            settings={
                "world_count": 1,
                "create_spoiler": True,
                "randomize_settings": False,
                "open_forest": "open",
                "open_door_of_time": True,
                "zora_fountain": "closed",
                "gerudo_fortress": "fast",
                "bridge": "stones",
                "triforce_hunt": False,
                "logic_rules": "glitchless",
                "all_reachable": True,
                "bombchus_in_logic": False,
                "one_item_per_dungeon": False,
                "trials_random": False,
                "trials": 0,
                "no_escape_sequence": True,
                "no_guard_stealth": True,
                "no_epona_race": True,
                "no_first_dampe_race": True,
                "useful_cutscenes": False,
                "fast_chests": True,
                "logic_no_night_tokens_without_suns_song": False,
                "free_scarecrow": False,
                "start_with_rupees": False,
                "start_with_consumables": False,
                "starting_hearts": 3,
                "chicken_count_random": False,
                "chicken_count": 7,
                "big_poe_count_random": False,
                "big_poe_count": 1,
                "shuffle_kokiri_sword": True,
                "shuffle_ocarinas": False,
                "shuffle_weird_egg": False,
                "shuffle_gerudo_card": False,
                "shuffle_song_items": False,
                "shuffle_cows": False,
                "shuffle_beans": False,
                "entrance_shuffle": "off",
                "shuffle_scrubs": "off",
                "shopsanity": "off",
                "tokensanity": "off",
                "shuffle_mapcompass": "startwith",
                "shuffle_smallkeys": "dungeon",
                "shuffle_bosskeys": "dungeon",
                "shuffle_ganon_bosskey": "lacs_vanilla",
                "enhance_map_compass": False,
                "mq_dungeons_random": False,
                "mq_dungeons": 0,
                "disabled_locations": [
                    "Deku Theater Mask of Truth"
                ],
                "allowed_tricks": [
                    "logic_fewer_tunic_requirements",
                    "logic_grottos_without_agony",
                    "logic_child_deadhand",
                    "logic_man_on_roof",
                    "logic_dc_jump",
                    "logic_rusted_switches",
                    "logic_windmill_poh",
                    "logic_crater_bean_poh_with_hovers",
                    "logic_forest_vines",
                    "logic_goron_city_pot_with_strength"
                ],
                "logic_earliest_adult_trade": "prescription",
                "logic_latest_adult_trade": "claim_check",
                "logic_lens": "chest-wasteland",
                "starting_equipment": [],
                "starting_items": [],
                "starting_songs": [],
                "ocarina_songs": False,
                "correct_chest_sizes": False,
                "clearer_hints": True,
                "hints": "always",
                "hint_dist": "tournament",
                "text_shuffle": "none",
                "ice_trap_appearance": "junk_only",
                "junk_ice_traps": "normal",
                "item_pool_value": "balanced",
                "damage_multiplier": "normal",
                "starting_tod": "default",
                "starting_age": "child"
            }
        )

        self.seed_id = self.seed['id']
        self.permalink = f"https://ootrandomizer.com/seed/get?id={self.seed['id']}"
        self.goal_postfix = f" - {self.permalink}"

    # Super Mario Bros 3 Rando
    async def event_sglive2020smb3(self):
        self.seed_id, flags = randomizer.roll_smb3r(
            '17BAS2LNJ4')
        self.permalink = f"Seed: {self.seed_id} - Flags: {flags}"
        self.goal_postfix = f" - {self.permalink}"

    @property
    def versus(self):
        return ' vs. '.join([p.display_name for p in self.players])

    @property
    def player_discords(self):
        return [(p.display_name, p.discord_user) for p in self.players]

    @property
    def player_mentionables(self):
        return [p.discord_user.mention for p in self.players]

    @property
    def event_slug(self):
        return self.episode_data['event']['slug']

    @property
    def event_name(self):
        return self.episode_data['event']['name']

    @property
    def episode_id(self):
        return self.episode_data['id']


async def create_smm2_match_discord(episode_id):
    race = await sgl2020_tournament.get_tournament_race_by_episodeid(episode_id)
    if race:
        return False

    sgl_race = await SGLiveRace.construct(episode_id=episode_id)
    await sgl_race.create_seed()

    smm2_category_id = int(await config.get(sgl_race.guild.id, 'SGLSMM2Category'))

    match_channel = await sgl_race.guild.create_text_channel(
        slugify(f"smm2-{episode_id}-{sgl_race.versus}"),
        category=discord.utils.get(
            sgl_race.guild.categories, id=smm2_category_id),
        topic=f"{sgl_race.event_name} - {sgl_race.versus} - {sgl_race.permalink}"
    )

    audit_channel_id = await config.get(sgl_race.guild.id, 'SGLAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(f"SMM2 Match - Episode {sgl_race.episode_data['id']} - {match_channel.mention}")

    embed = discord.Embed(
        title=f"SMM2 Match Channel Opened - {sgl_race.event_name} - {sgl_race.versus}",
        description=f"Greetings!  The discord channel {match_channel.mention} has been opened.\n\nGLHF!",
        color=discord.Colour.blue(),
        timestamp=datetime.datetime.now()
    )

    for name, player in sgl_race.player_discords:
        if player is None:
            await audit_channel.send(f'Could not DM {name}. Could not lookup player in SG system.')
            continue
        try:
            await match_channel.set_permissions(player, read_messages=True)
            await player.send(embed=embed)
        except discord.HTTPException as e:
            await audit_channel.send(f'Could not add {name} to channel {match_channel.mention}')
            continue

    await sgl2020_tournament.insert_tournament_race(
        room_name=match_channel.id,
        episode_id=episode_id,
        permalink=sgl_race.permalink,
        seed=sgl_race.seed_id,
        password=None,
        event=sgl_race.episode_data['event']['slug'],
        platform='discord'
    )

    await match_channel.send(f"Welcome {', '.join(sgl_race.player_mentionables)}!  ")
    return match_channel


async def process_sgl_race(handler, episode_id=None):
    await handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

    race = await sgl2020_tournament.get_active_tournament_race(handler.data.get('name'))
    if race:
        episodeid = race.get('episode_id')
    if race is None and episodeid is None:
        await handler.send_message("Please provide an SG episode ID.")
        return

    try:
        sgl_race = await SGLiveRace.construct(episode_id=episodeid)
    except Exception as e:
        logging.exception("Problem creating SGL race.")
        await handler.send_message(f"Could not process league race: {str(e)}")
        return

    try:
        await sgl_race.create_seed()
    except Exception as e:
        logging.exception("Problem rolling SGL race.")
        await handler.send_message(f"Could not process league race: {str(e)}")
        return

    await handler.set_raceinfo(f"{sgl_race.event_name} - {sgl_race.versus}{sgl_race.goal_postfix}", overwrite=True)
    await handler.send_message(sgl_race.permalink)

    embed = discord.Embed(
        title=f"{sgl_race.event_name} - {sgl_race.versus}",
        color=discord.Colour.red(),
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="Permalink", value=sgl_race.permalink, inline=False)
    if sgl_race.bingo_password:
        embed.add_field(name="Bingosync Password",
                        value=sgl_race.bingo_password)
    embed.add_field(
        name="RT.gg", value=f"https://racetime.gg{handler.data['url']}", inline=False)

    audit_channel_id = await config.get(sgl_race.guild.id, 'SGLAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(embed=embed)

    await sgl2020_tournament.insert_tournament_race(
        room_name=handler.data.get('name'),
        episode_id=episodeid,
        permalink=sgl_race.permalink,
        seed=sgl_race.seed_id,
        password=sgl_race.bingo_password,
        event=sgl_race.episode_data['event']['slug'],
        platform='racetime'
    )

    await handler.send_message("Seed has been generated and should now be in the race info.")
    handler.seed_rolled = True


async def process_sgl_race_start(handler):
    race_id = handler.data.get('name')

    if race_id is None:
        return

    race = await sgl2020_tournament.get_active_tournament_race(race_id)

    if race is None:
        return

    if race['event'] == 'sglive2020smo':
        await randomizer.bingosync.new_card(
            config={
                'hide_card': False,
                'game_type': 45,
                'variant_type': 45,
                'custom_json': '',
                'lockout_mode': 1,
                'seed': '',
                'room': race['seed']
            }
        )

    await sgl2020_tournament.update_tournament_race_status(race_id, "STARTED")
    await handler.send_message("Please double check your stream and ensure that it is displaying your game!  GLHF")


async def create_sgl_race_room(episode_id):
    rtgg_sgl = alttprbot_racetime.bot.racetime_bots['sgl']
    race = await sgl2020_tournament.get_tournament_race_by_episodeid(episode_id)
    if race:
        async with aiohttp.request(
                method='get',
                url=rtgg_sgl.http_uri(f"/{race['room_name']}/data"),
                raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await sgl2020_tournament.delete_active_tournament_race(race['room_name'])

    sgl_race = await SGLiveRace.construct(episode_id=episode_id)

    handler = await rtgg_sgl.create_race(
        config={
            'goal': EVENTS[sgl_race.event_slug]['rtgg_goal'],
            'custom_goal': '',
            # 'invitational': 'on',
            'unlisted': 'on',
            'info': f"{sgl_race.event_name} - {sgl_race.versus}",
            'start_delay': 15,
            'time_limit': 24,
            'streaming_required': 'on',
            'allow_comments': 'on',
            'allow_midrace_chat': 'on',
            'chat_message_delay': 0})

    print(handler.data.get('name'))
    await sgl2020_tournament.insert_tournament_race(
        room_name=handler.data.get('name'),
        episode_id=sgl_race.episode_id,
        event=sgl_race.episode_data['event']['slug'],
        platform='racetime'
    )

    embed = discord.Embed(
        title=f"RT.gg Room Opened - {sgl_race.event_name} - {sgl_race.versus}",
        description=f"Greetings!  A RaceTime.gg race room has been automatically opened for you.\nYou may access it at https://racetime.gg{handler.data['url']}\n\nEnjoy!",
        color=discord.Colour.blue(),
        timestamp=datetime.datetime.now()
    )

    audit_channel_id = await config.get(sgl_race.guild.id, 'SGLAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(embed=embed)

    for name, player in sgl_race.player_discords:
        if player is None:
            await audit_channel.send(f'Could not DM {name}')
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            await audit_channel.send(f'Could not send room opening DM to {name}')
            continue

    return handler.data


async def scan_sgl_schedule():
    guild_id = await config.get(0, 'SGLAuditChannel')
    audit_channel_id = await config.get(guild_id, 'SGLAuditChannel')
    audit_channel = discordbot.get_channel(int(audit_channel_id))

    if c.DEBUG:
        events = ['test']
    else:
        events = EVENTS.keys()
    print("SGL - scanning SG schedule for races to create")
    for event in events:
        try:
            episodes = await speedgaming.get_upcoming_episodes_by_event(event, hours_past=0.5, hours_future=.75)
        except Exception as e:
            logging.exception(
                "Encountered a problem when attempting to retrieve SG schedule.")
            if audit_channel:
                await audit_channel.send(
                    f"There was an error while trying to scan schedule for {event}`.\n\n{str(e)}")
            continue
        for episode in episodes:
            print(episode['id'])
            try:
                await create_sgl_match(episode)
            except Exception as e:
                logging.exception(
                    "Encountered a problem when attempting to create RT.gg race room.")
                if audit_channel:
                    await audit_channel.send(
                        f"@here There was an error while automatically creating a race room for episode `{episode['id']}`.\n\n{str(e)}",
                        allowed_mentions=discord.AllowedMentions(
                            everyone=True)
                    )

    print('done')


async def race_recording_task():
    guild_id = await config.get(0, 'SGLAuditChannel')
    audit_channel_id = await config.get(guild_id, 'SGLAuditChannel')
    audit_channel = discordbot.get_channel(int(audit_channel_id))

    races = await sgl2020_tournament.get_unrecorded_races()
    for race in races:
        print(race['episode_id'])
        try:
            await record_episode(race)
        except Exception as e:
            logging.exception(
                "Encountered a problem when attempting to record a race.")
            if audit_channel:
                await audit_channel.send(
                    f"There was an error while automatically creating a race room for episode `{race['episode_id']}`.\n\n{str(e)}")

    print('done')


async def create_sgl_match(episode):
    if episode['event']['slug'] not in EVENTS.keys():
        raise Exception(
            f"{episode['id']} is not an SGL match.  Found {episode['event']['slug']}")

    if episode['event']['slug'] == 'sglive2020smm2':
        await create_smm2_match_discord(episode['id'])
    else:
        await create_sgl_race_room(episode['id'])


async def record_episode(race):
    # do a bunch of stuff to write the race to the spreadsheet
    if race['status'] == "RECORDED":
        return

    sheet_name = EVENTS[race['event']].get('sheet')

    agcm = gspread_asyncio.AsyncioGspreadClientManager(gsheet.get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(SGL_RESULTS_SHEET)
    wks = await wb.worksheet(sheet_name)

    if race['platform'] == 'racetime':
        async with aiohttp.request(
                method='get',
                url=f"https://racetime.gg/{race['room_name']}/data",
                raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())

        if race_data['status']['value'] == 'finished':
            winner = [e for e in race_data['entrants'] if e['place'] == 1][0]
            runnerup = [e for e in race_data['entrants']
                        if e['place'] in [2, None]][0]

            await wks.append_row(values=[
                race['episode_id'],
                f"https://racetime.gg/{race['room_name']}",
                winner['user']['name'],
                runnerup['user']['name'],
                str(isodate.parse_duration(winner['finish_time'])) if isinstance(
                    winner['finish_time'], str) else None,
                str(isodate.parse_duration(runnerup['finish_time'])) if isinstance(
                    runnerup['finish_time'], str) else None,
                race['permalink'],
                race['password'],
                str(race['created']),
                str(race['updated'])
            ])
        if race_data['status']['value'] == 'cancelled':
            await sgl2020_tournament.delete_active_tournament_race(race['room_name'])
    else:
        episode_data = await speedgaming.get_episode(race['episode_id'])
        await wks.append_row(values=[
            race['episode_id'],
            None,
            episode_data['match1']['players'][0]['displayName'],
            episode_data['match1']['players'][1]['displayName'],
            None,
            None,
            race['permalink'],
            race['password'],
            str(race['created']),
            str(race['updated'])
        ])

    await sgl2020_tournament.update_tournament_race_status(race['room_name'], "RECORDED")


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
