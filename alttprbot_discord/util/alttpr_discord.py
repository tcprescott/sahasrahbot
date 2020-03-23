import datetime

import discord
import html2markdown
from pyz3r.alttpr import alttprClass

from config import Config as c

emoji_code_map = {
    'Bow': 'Bow',
    'Boomerang': 'BestBoomerang',
    'Hookshot': 'Hookshot',
    'Bombs': 'Blowup',
    'Mushroom': 'Mushroom',
    'Magic Powder': 'Powder',
    'Ice Rod': 'IceRod',
    'Pendant': 'PendantOfCourage',
    'Bombos': 'Bombos',
    'Ether': 'Ether',
    'Quake': 'Quake',
    'Lamp': 'Lamp',
    'Hammer': 'MCHammer',
    'Shovel': 'shovel',
    'Flute': 'Flute',
    'Bugnet': 'BugNet',
    'Book': 'Mudora',
    'Empty Bottle': 'EmptyBottle',
    'Green Potion': 'GreenPotion',
    'Somaria': 'somaria',
    'Cape': 'Cape',
    'Mirror': 'mirror',
    'Boots': 'GoFast',
    'Gloves': 'PowerGlove',
    'Flippers': 'Flippers',
    'Moon Pearl': 'MoonPearl',
    'Shield': 'MirrorShield',
    'Tunic': 'GreenTunic',
    'Heart': 'ALotOfLove',
    'Map': 'DungeonMap',
    'Compass': 'DungeonCompass',
    'Big Key': 'BigKey'
}

async def alttpr(settings=None, hash_id=None, customizer=False, festive=False):
    seed = alttprDiscordClass(settings=settings, hash_id=hash_id, customizer=customizer, festive=festive)
    await seed._init()
    return seed

class alttprDiscordClass(alttprClass):
    def __init__(self, *args, **kwargs):
        super(alttprDiscordClass, self).__init__(*args, **kwargs)
        self.seed_baseurl = c.seed_baseurl
        self.baseurl = c.baseurl
        self.username = c.username
        self.password = c.password

    async def embed(self, emojis=False, name=False, notes=False):
        if not name:
            try:
                name = self.data['spoiler']['meta']['name']
            except KeyError:
                name = 'Requested Seed'

        if not notes:
            try:
                notes = html2markdown.convert(self.data['spoiler']['meta']['notes'])
            except KeyError:
                notes = ""

        settings_map = await self.randomizer_settings()

        embed = discord.Embed(
            title=name,
            description=notes,
            color=discord.Colour.dark_red(),
            timestamp=datetime.datetime.fromisoformat(self.data['generated'])
        )

        if self.data['spoiler']['meta'].get('special',False):
            embed.add_field(
                name='Festive Randomizer',
                value="This game is a festive randomizer.  Happy holidays!",
                inline=False)

        if self.data['spoiler']['meta'].get('spoilers','off') == "mystery":
            embed.add_field(
                name='Mystery Game',
                value="No meta information is available for this game.",
                inline=False)
            embed.add_field(
                name='Item Placement',
                value=f"**Logic:** {self.data['spoiler']['meta']['logic']}",
                inline=True)
        else:
            embed.add_field(
                name='Item Placement',
                value="**Logic:** {logic}\n**Item Placement:** {item_placement}\n**Dungeon Items:** {dungeon_items}\n**Accessibility:** {accessibility}".format(
                    logic=self.data['spoiler']['meta']['logic'],
                    item_placement=settings_map['item_placement'][self.data['spoiler']['meta']['item_placement']],
                    dungeon_items=settings_map['dungeon_items'][self.data['spoiler']['meta']['dungeon_items']],
                    accessibility=settings_map['accessibility'][self.data['spoiler']['meta']['accessibility']],
                ),
                inline=True)

            embed.add_field(
                name='Goal',
                value="**Goal:** {goal}\n**Open Tower:** {tower}\n**Ganon Vulnerable:** {ganon}".format(
                    goal=settings_map['goals'][self.data['spoiler']['meta']['goal']],
                    tower=self.data['spoiler']['meta'].get('entry_crystals_tower', 'unknown'),
                    ganon=self.data['spoiler']['meta'].get('entry_crystals_ganon', 'unknown'),
                ),
                inline=True)
            embed.add_field(
                name='Gameplay',
                value="**World State:** {mode}\n**Entrance Shuffle:** {entrance}\n**Boss Shuffle:** {boss}\n**Enemy Shuffle:** {enemy}\n**Hints:** {hints}".format(
                    mode=settings_map['world_state'][self.data['spoiler']['meta']['mode']],
                    entrance=settings_map['entrance_shuffle'][self.data['spoiler']['meta']['shuffle']] if 'shuffle' in self.data['spoiler']['meta'] else "None",
                    boss=settings_map['boss_shuffle'][self.data['spoiler']['meta']['enemizer.boss_shuffle']],
                    enemy=settings_map['enemy_shuffle'][self.data['spoiler']['meta']['enemizer.enemy_shuffle']],
                    hints=self.data['spoiler']['meta']['hints']
                ),
                inline=True)
            embed.add_field(
                name='Difficulty',
                value="**Swords:** {weapons}\n**Item Pool:** {pool}\n**Item Functionality:** {functionality}\n**Enemy Damage:** {damage}\n**Enemy Health:** {health}".format(
                    weapons=settings_map['weapons'][self.data['spoiler']['meta']['weapons']],
                    pool=settings_map['item_pool'][self.data['spoiler']['meta']['item_pool']],
                    functionality=settings_map['item_functionality'][self.data['spoiler']['meta']['item_functionality']],
                    damage=settings_map['enemy_damage'][self.data['spoiler']['meta']['enemizer.enemy_damage']],
                    health=settings_map['enemy_health'][self.data['spoiler']['meta']['enemizer.enemy_health']],
                ),
                inline=True)

        code = await self.code()
        embed.add_field(name='File Select Code', value=await build_file_select_code(code, emojis=emojis), inline=False)

        embed.add_field(name='Permalink', value=self.url, inline=False)

        embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
        return embed


    async def tournament_embed(self, emojis=False, name=False, notes=False):
        if not name:
            try:
                name = self.data['spoiler']['meta']['name']
            except KeyError:
                name = 'Requested Seed'

        if not notes:
            try:
                notes = html2markdown.convert(self.data['spoiler']['meta']['notes'])
            except KeyError:
                notes = ""

        settings_map = await self.randomizer_settings()

        embed = discord.Embed(
            title=name,
            description=notes,
            color=discord.Colour.dark_gold(),
            timestamp=datetime.datetime.fromisoformat(self.data['generated'])
        )

        if self.data['spoiler']['meta'].get('spoilers','off') == "mystery":
            embed.add_field(
                name='Mystery Game',
                value="No meta information is available for this game.",
                inline=False)
            embed.add_field(
                name='Item Placement',
                value=f"**Logic:** {self.data['spoiler']['meta']['logic']}",
                inline=True)
        else:
            embed.add_field(
                name='Settings',
                value=f"**Logic:** {self.data['spoiler']['meta']['logic']}\n**Dungeon Items:** {settings_map['dungeon_items'][self.data['spoiler']['meta']['dungeon_items']]}\n**Goal:** {settings_map['goals'][self.data['spoiler']['meta']['goal']]}\n**Open Tower:** {self.data['spoiler']['meta']['entry_crystals_tower']}\n**Ganon Vulnerable:** {self.data['spoiler']['meta']['entry_crystals_ganon']}\n**World State:** {settings_map['world_state'][self.data['spoiler']['meta']['mode']]}\n**Swords:** {settings_map['weapons'][self.data['spoiler']['meta']['weapons']]}"
            )

        code = await self.code()
        embed.add_field(name='File Select Code', value=await build_file_select_code(code, emojis=emojis), inline=False)

        embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
        return embed

async def build_file_select_code(code, emojis=None):
    if emojis:
        emoji_list = list(map(lambda x: str(discord.utils.get(
            emojis, name=emoji_code_map[x])), code))
        return ' '.join(emoji_list) + ' (' + '/'.join(code) + ')'
    else:
        return '/'.join(code)
