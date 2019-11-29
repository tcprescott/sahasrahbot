from pyz3r.alttpr import alttprClass 
from html.parser import HTMLParser
import discord
from config import Config as c

async def alttpr(settings=None, hash=None, customizer=False):
    seed = alttprDiscordClass(settings=settings, hash=hash, customizer=customizer)
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
                notes = strip_tags(self.data['spoiler']['meta']['notes'])
            except KeyError:
                notes = ""

        settings_map = await self.randomizer_settings()

        embed = discord.Embed(
            title=name,
            description=notes,
            color=discord.Colour.dark_red())

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
                    tower=self.data['spoiler']['meta']['entry_crystals_tower'],
                    ganon=self.data['spoiler']['meta']['entry_crystals_ganon'],
                ),
                inline=True)
            embed.add_field(
                name='Gameplay',
                value="**World State:** {mode}\n**Entrance Shuffle:** {entrance}\n**Boss Shuffle:** {boss}\n**Enemy Shuffle:** {enemy}\n**Hints:** {hints}".format(
                    mode=settings_map['world_state'][self.data['spoiler']['meta']['mode']],
                    entrance="None" if not 'shuffle' in self.data['spoiler']['meta'] else settings_map['entrance_shuffle'][self.data['spoiler']['meta']['shuffle']],
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

        if emojis:
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
            code = await self.code()
            c = list(map(lambda x: str(discord.utils.get(
                emojis, name=emoji_code_map[x])), code))
            embed.add_field(name='File Select Code', value=' '.join(
                c) + ' (' + '/'.join(code) + ')', inline=False)
        else:
            code = await self.code()
            embed.add_field(
                name='File Select Code',
                value='/'.join(code),
                inline=False)

        embed.add_field(name='Permalink', value=self.url, inline=False)
        return embed

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()
