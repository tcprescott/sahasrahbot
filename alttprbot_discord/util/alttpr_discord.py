import datetime
import os

import aiohttp
import discord
import html2markdown

from pyz3r.alttpr import alttprClass

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
    seed = alttprDiscordClass(
        settings=settings, hash_id=hash_id, customizer=customizer, festive=festive)
    await seed._init()
    return seed


class alttprDiscordClass(alttprClass):
    def __init__(self, *args, **kwargs):
        super(alttprDiscordClass, self).__init__(*args, **kwargs)
        self.baseurl = os.environ.get(
            "ALTTPR_BASEURL", 'https://alttpr.com')
        self.seed_baseurl = os.environ.get(
            "ALTTPR_SEED_BASEURL", "https://s3.us-east-2.amazonaws.com/alttpr-patches")
        username = os.environ.get("ALTTPR_USERNAME", None)
        password = os.environ.get("ALTTPR_PASSWORD", None)
        self.auth = aiohttp.BasicAuth(login=username, password=password) if username and password else None

    @property
    def generated_goal(self):
        settings_list = []
        meta = self.data['spoiler'].get('meta', {})

        if meta.get('spoilers', 'off') == 'mystery':
            return 'mystery'

        settings = {
            'mode': meta.get('mode', 'open'),
            'weapons': meta.get('weapons', 'randomized'),
            'goal': meta.get('goal', 'ganon'),
            'logic': meta.get('logic', 'NoGlitches'),
            'shuffle': meta.get('shuffle', 'none'),
            'item_pool': meta.get('item_pool', 'normal'),
            'dungeon_items': meta.get('dungeon_items', 'standard'),
            'item_functionality': meta.get('item_functionality', 'normal'),
            'entry_crystals_ganon': meta.get('entry_crystals_ganon', '7'),
            'entry_crystals_tower': meta.get('entry_crystals_tower', '7'),
            'enemizer.boss_shuffle': meta.get('enemizer.boss_shuffle', 'none'),
            'enemizer.enemy_damage': meta.get('enemizer.enemy_damage', 'default'),
            'enemizer.enemy_health': meta.get('enemizer.enemy_health', 'default'),
            'enemizer.enemy_shuffle': meta.get('enemizer.enemy_shuffle', 'none'),
        }

        if not settings['item_pool'] in ['easy', 'normal'] or not settings['item_functionality'] in ['easy', 'normal']:
            settings_list.append('hard')
        elif settings['dungeon_items'] == 'full' and not settings['goal'] == 'dungeons':
            settings_list.append('normal')

        if is_enemizer(settings):
            settings_list.append("enemizer")

        if settings['weapons'] == 'swordless':
            settings_list.append('swordless')

        if not (settings['dungeon_items'] == 'full' and settings['goal'] == 'dungeons'):
            if settings['mode'] == 'open':
                if settings['shuffle'] == 'none' and not is_enemizer(settings) and (settings['item_pool'] == 'normal' and settings['item_functionality'] == 'normal') and not settings['weapons'] == 'swordless':
                    settings_list.append('casual')
                settings_list.append('open')
            elif settings['mode'] == 'standard' and settings['weapons'] == 'randomized':
                settings_list.append('standard')
            elif settings['mode'] == 'standard' and settings['weapons'] == 'assured' and (settings['item_pool'] == 'normal' and settings['item_functionality'] == 'normal'):
                settings_list.append('casual')
            elif settings['mode'] == 'inverted':
                settings_list.append('inverted')
            elif settings['mode'] == 'retro':
                settings_list.append('retro')

        if settings['goal'] == 'OverworldGlitches':
            settings_list.append("overworld glitches")
        elif settings['goal'] == 'MajorGlitches':
            settings_list.append("major glitches")
        elif settings['goal'] == 'NoLogic':
            settings_list.append("no logic")

        if not settings['entry_crystals_tower'] == '7' or not settings['entry_crystals_ganon'] == '7':
            settings_list.append(
                f"{settings['entry_crystals_tower']}/{settings['entry_crystals_ganon']}")

        if settings['goal'] == 'ganon' and settings['shuffle'] != 'none':
            settings_list.append("defeat ganon")
        elif settings['goal'] == 'fast_ganon' and settings['shuffle'] == 'none':
            settings_list.append("fast ganon")
        elif settings['goal'] == 'dungeons':
            settings_list.append("all dungeons")
        elif settings['goal'] == 'triforce-hunt':
            settings_list.append("triforce hunt")
        elif settings['goal'] == 'pedestal':
            settings_list.append("pedestal")

        if settings['dungeon_items'] == 'mc':
            settings_list.append("mc")
        elif settings['dungeon_items'] == 'mcs':
            settings_list.append("mcs")
        elif settings['dungeon_items'] == 'full':
            settings_list.append("keysanity")

        if not settings['shuffle'] == 'none':
            settings_list.append("+ entrance shuffle")

        if meta.get('difficulty', None) == 'custom':
            settings_list.append("(customizer)")

        return " ".join(settings_list)

    async def embed(self, emojis=False, name=False, notes=False):
        settings_map = await self.randomizer_settings()

        meta = self.data['spoiler'].get('meta', {})

        embed = discord.Embed(
            title=meta.get('name', 'Requested Seed') if not name else name,
            description=html2markdown.convert(
                meta.get('notes', '')) if not notes else notes,
            color=discord.Colour.dark_red(),
            timestamp=datetime.datetime.fromisoformat(self.data['generated'])
        )

        if meta.get('special', False):
            embed.add_field(
                name='Festive Randomizer',
                value="This game is a festive randomizer.  Happy holidays!",
                inline=False)

        if meta.get('spoilers', 'off') == "mystery":
            embed.add_field(
                name='Mystery Game',
                value="No meta information is available for this game.",
                inline=False)
            embed.add_field(
                name='Item Placement',
                value=f"**Logic:** {meta['logic']}",
                inline=True)
        else:
            embed.add_field(
                name='Item Placement',
                value="**Logic:** {logic}\n**Item Placement:** {item_placement}\n**Dungeon Items:** {dungeon_items}\n**Accessibility:** {accessibility}".format(
                    logic=meta['logic'],
                    item_placement=settings_map['item_placement'][meta['item_placement']],
                    dungeon_items=settings_map['dungeon_items'][meta['dungeon_items']],
                    accessibility=settings_map['accessibility'][meta['accessibility']],
                ),
                inline=True)

            embed.add_field(
                name='Goal',
                value="**Goal:** {goal}\n**Open Tower:** {tower}\n**Ganon Vulnerable:** {ganon}".format(
                    goal=settings_map['goals'][meta['goal']],
                    tower=meta.get(
                        'entry_crystals_tower', 'unknown'),
                    ganon=meta.get(
                        'entry_crystals_ganon', 'unknown'),
                ),
                inline=True)
            embed.add_field(
                name='Gameplay',
                value="**World State:** {mode}\n**Entrance Shuffle:** {entrance}\n**Boss Shuffle:** {boss}\n**Enemy Shuffle:** {enemy}\n**Pot Shuffle:** {pot}\n**Hints:** {hints}".format(
                    mode=settings_map['world_state'][meta['mode']],
                    entrance=settings_map['entrance_shuffle'][meta['shuffle']
                                                              ] if 'shuffle' in meta else "None",
                    boss=settings_map['boss_shuffle'][meta['enemizer.boss_shuffle']],
                    enemy=settings_map['enemy_shuffle'][meta['enemizer.enemy_shuffle']],
                    pot=meta.get('enemizer.pot_shuffle', 'off'),
                    hints=meta['hints']
                ),
                inline=True)
            embed.add_field(
                name='Difficulty',
                value="**Swords:** {weapons}\n**Item Pool:** {pool}\n**Item Functionality:** {functionality}\n**Enemy Damage:** {damage}\n**Enemy Health:** {health}".format(
                    weapons=settings_map['weapons'][meta['weapons']],
                    pool=settings_map['item_pool'][meta['item_pool']],
                    functionality=settings_map['item_functionality'][meta['item_functionality']],
                    damage=settings_map['enemy_damage'][meta['enemizer.enemy_damage']],
                    health=settings_map['enemy_health'][meta['enemizer.enemy_health']],
                ),
                inline=True)

        embed.add_field(name='File Select Code', value=self.build_file_select_code(
            emojis=emojis), inline=False)

        embed.add_field(name='Permalink', value=self.url, inline=False)

        embed.set_footer(text="Generated", icon_url=discord.utils.get(
            emojis, name="SahasrahBot").url)
        return embed

    async def tournament_embed(self, emojis=False, name=False, notes=False):
        settings_map = await self.randomizer_settings()

        meta = self.data['spoiler'].get('meta', {})

        embed = discord.Embed(
            title=meta.get('name', 'Requested Seed') if not name else name,
            description=html2markdown.convert(
                meta.get('notes', '')) if not notes else notes,
            color=discord.Colour.dark_gold(),
            timestamp=datetime.datetime.fromisoformat(self.data['generated'])
        )

        if meta.get('spoilers', 'off') == "mystery":
            embed.add_field(
                name='Mystery Game',
                value="No meta information is available for this game.",
                inline=False)
            embed.add_field(
                name='Item Placement',
                value=f"**Logic:** {meta['logic']}",
                inline=True)
        else:
            embed.add_field(
                name='Settings',
                value=(
                    f"**Logic:** {meta['logic']}\n"
                    f"**Dungeon Items:** {settings_map['dungeon_items'][meta['dungeon_items']]}\n"
                    f"**Goal:** {settings_map['goals'][meta['goal']]}\n"
                    f"**World State:** {settings_map['world_state'][meta['mode']]}\n"
                    f"**Swords:** {settings_map['weapons'][meta['weapons']]}}\n"
                    f"**Enemy Shuffle:** {settings_map['enemy_shuffle'][meta['enemizer.enemy_shuffle']]}\n"
                    f"**Boss Shuffle:** {settings_map['boss_shuffle'][meta['enemizer.boss_shuffle']]}\n"
                )
            )

        embed.add_field(name='File Select Code', value=self.build_file_select_code(
            emojis=emojis), inline=False)

        embed.set_footer(text="Generated", icon_url=discord.utils.get(
            emojis, name="SahasrahBot").url)
        return embed

    def build_file_select_code(self, emojis=None):
        if emojis:
            emoji_list = list(map(lambda x: str(discord.utils.get(
                emojis, name=emoji_code_map[x])), self.code))
            return ' '.join(emoji_list) + ' (' + '/'.join(self.code) + ')'
        else:
            return '/'.join(self.code)


def is_enemizer(settings):
    return settings['enemizer.boss_shuffle'] != 'none' or settings['enemizer.enemy_shuffle'] != 'none' or settings['enemizer.enemy_damage'] != 'default' or settings['enemizer.enemy_health'] != 'default'
