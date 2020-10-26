import datetime
import json
import logging

import aiohttp
import discord
from alttprbot.database import config, sgl2020_tournament
from alttprbot.alttprgen import randomizer
from alttprbot.alttprgen import preset as preset
from alttprbot.util import speedgaming
from alttprbot_discord.bot import discordbot
from alttprbot_racetime.bot import racetime_bots

GOALS = {
    'sglive2020alttpr': 1450,
    'sglive2020aosr': 1458,
    'sglive2020cv1': 1459,
    'sglive2020ffr': 1452,
    'sglive2020mmx': 1462,
    'sglive2020smz3': 1455,
    'sglive2020smm2': 1460,
    'sglive2020smo': 1461,
    'sgl2020smany': 1453,
    'sgl2020smdab': 1454,
    'sglive2020smr': 1456,
    'sglive2020z1r': 1457,
    'sglive2020ootr': 1451,
    'sglive2020smb3': 1463
}

class SpeedGamingUser():
    def __init__(self, guild, player):
        self.display_name = player['displayName']
        self.public_stream = player['publicStream']
        self.streaming_from = player['streamingFrom']
        self.discord_id = player['discordId']
        self.discord_tag = player['discordTag']

        if member := guild.get_member(int(player['discordId'])):
            self.discord_user = member
        elif member := guild.get_member_named(player['discordTag']):
            self.discord_user = member
        elif member := guild.get_member_named(player['displayName']):
            self.discord_user = member
        else:
            self.discord_user = None

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

    async def create_seed(self):
        method = f'event_{self.event_slug}'
        if hasattr(self, method):
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

        # Optional Value
        self.code = '/'.join(self.seed.code)

    # AOSR
    async def event_sglive2020aosr(self):
        self.seed_id, self.permalink = randomizer.roll_aosr(logic='AreaTechTeirs', panther='Rand70Dup', boss='Vanilla', kicker='false')

    # Castlevania 1
    # async def event_sglive2020cv1(self):
    #     pass

    # Final Fantasy Randomizer
    async def event_sglive2020ffr(self):
        self.seed_id, self.permalink = randomizer.roll_ffr(flags='yGcifaseK8fJxIkkAzUzYAzx32UoP5toiyJrTE864J9FEyMsXe5XhM5T94nANOh1T6wJN7BZU4p3r3WORe9o7vyXSpZD')

    # Megaman X
    # async def event_sglive2020mmx(self):
    #     pass

    # SMZ3
    async def event_sglive2020smz3(self):
        self.seed, self.preset_dict = await preset.get_preset('normal', randomizer='smz3')

        # Two mandatory values
        self.permalink = self.seed.url
        self.seed_id = self.seed.hash

        # Optional
        self.code = self.seed.code

    # Super Mario Maker 2
    async def event_sglive2020smm2(self):
        pass

    # SMO
    async def event_sglive2020smo(self):
        pass

    # SM Any%
    async def event_sgl2020smany(self):
        pass

    # SM DAB
    async def event_sgl2020smdab(self):
        pass

    # Super Metroid Randomizer
    async def event_sglive2020smr(self):
        pass

    # Zelda 1 Randomizer
    async def event_sglive2020z1r(self):
        pass

    # Ocarina of Time Randomizer
    async def event_sglive2020ootr(self):
        pass

    #Super Mario Bros 3 Rando
    async def event_sglive2020smb3(self):
        pass

    @property
    def versus(self):
        return ' vs. '.join([p.display_name for p in self.players])

    @property
    def player_discords(self):
        return [(p.display_name, p.discord_user) for p in self.players]

    @property
    def event_slug(self):
        return self.episode_data['event']['slug']

    @property
    def event_name(self):
        return self.episode_data['event']['name']

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
        logging.exception("Problem creating league race.")
        await handler.send_message(f"Could not process league race: {str(e)}")
        return

    goal = f"SGL 2020 - {sgl_race.game} - {sgl_race.versus}"

    await handler.set_raceinfo(f"{goal}", overwrite=True)

    await sgl2020_tournament.insert_tournament_race(
        room_name=handler.data.get('name'),
        episode_id=episode_id,
        permalink=sgl_race.permalink,
        seed=sgl_race.seed_id,
        event=sgl_race.episode_data['event']['slug'],
    )

    await handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a League Moderator if you haven't received the DM.")
    handler.seed_rolled = True


async def create_sgl_race_room(episode_id):
    rtgg_sgl = racetime_bots['sgl']
    race = await sgl2020_tournament.get_active_tournament_race_by_episodeid(episode_id)
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

    sgl_race = await SGLiveRace.construct(episode_id=episode_id, create_seed=False)

    handler = await rtgg_sgl.create_race(
        config={
            'goal': GOALS[sgl_race.event_slug],
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
        event=sgl_race.episode_data['event']['slug']
    )

    # for rtggid in [p.data['rtgg_id'] for p in league_race.players]:
    #     await handler.invite_user(rtggid)

    embed = discord.Embed(
        title=f"RT.gg Room Opened - {sgl_race.event_name} - {sgl_race.versus}",
        description=f"Greetings!  A RaceTime.gg race room has been automatically opened for you.\nYou may access it at https://racetime.gg{handler.data['url']}\n\nEnjoy!",
        color=discord.Colour.blue(),
        timestamp=datetime.datetime.now()
    )

    for name, player in sgl_race.player_discords:
        if player is None:
            print(f'Could not DM {name}')
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            print(f'Could not send room opening DM to {name}')
            continue

    await handler.send_message('Welcome. Use !roll (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of you race.  If you need help, ping @Mods in the ALTTPR League Discord.')
    return handler.data
