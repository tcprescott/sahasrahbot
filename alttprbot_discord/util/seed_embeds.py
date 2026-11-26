"""Discord embeds for generated seeds.

The randomizer clients in ``alttprbot/alttprgen/`` only generate and describe
seeds. Everything Discord-specific about showing a seed (embeds, colours,
file select code emojis) lives here.

Use ``seed_embed`` / ``seed_tournament_embed`` when the seed could come from
any randomizer; they pick the right builder for the seed's type.
"""
import datetime
import inspect

import discord
import html2markdown
from pyz3r import ALTTPR
from pyz3r.sm import smClass
from pyz3r.smvaria import SuperMetroidVaria

from alttprbot.alttprgen.randomizer.alttprdoor import AlttprDoor
from alttprbot.alttprgen.randomizer.avianart import AVIANART

DOOR_RANDOMIZER = 'Door Randomizer'
REQUESTED_SEED = "Requested Seed"
FILE_SELECT_CODE = 'File Select Code'

# File select code item name -> SahasrahBot custom emoji name.
EMOJI_CODE_MAP = {
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


FOOTER_EMOJI = "SahasrahBot"


def usable_emojis(emojis, permissions: discord.Permissions | None):
    """The emojis an embed may show where the bot has ``permissions``.

    The file select code emojis live on SahasrahBot's own server, so they're external
    everywhere else: without "Use External Emojis" Discord shows them as ``:Bow:`` text
    (#52). Then only the footer emoji is kept (an icon is a plain image URL, which needs
    no permission), and the code falls back to text. ``None`` means no restriction.
    """
    if permissions is None or permissions.use_external_emojis:
        return emojis
    return [emoji for emoji in emojis or [] if emoji.name == FOOTER_EMOJI]


def build_file_select_code(seed, emojis=None):
    """The seed's file select code, as emojis plus text when ``emojis`` has every one of them."""
    text = '/'.join(seed.code)
    if emojis:
        found = [discord.utils.get(emojis, name=EMOJI_CODE_MAP[x]) for x in seed.code]
        if all(found):
            return ' '.join(str(emoji) for emoji in found) + ' (' + text + ')'
    return text


def _footer_icon(emojis):
    emoji = discord.utils.get(emojis or [], name=FOOTER_EMOJI)
    return emoji.url if emoji else None


# --- ALTTPR (alttpr.com) ---

def _add_mystery_fields(embed, meta):
    embed.add_field(
        name='Mystery Game',
        value="No meta information is available for this game.",
        inline=False)
    embed.add_field(
        name='Item Placement',
        value=f"**Glitches Required:** {meta['logic']}",
        inline=True)


def _add_festive_fields(embed, meta, settings_map):
    embed.add_field(
        name='Festive Randomizer',
        value="This game is a festive randomizer.  Spooky!",
        inline=False)
    embed.add_field(
        name='Settings',
        value=(f"**Item Placement:** {settings_map['item_placement'][meta['item_placement']]}\n"
               f"**Dungeon Items:** {settings_map['dungeon_items'][meta['dungeon_items']]}\n"
               f"**Accessibility:** {settings_map['accessibility'][meta['accessibility']]}\n"
               f"**World State:** {settings_map['world_state'][meta['mode']]}\n"
               f"**Hints:** {meta['hints']}\n"
               f"**Swords:** {settings_map['weapons'][meta['weapons']]}\n"
               f"**Item Pool:** {settings_map['item_pool'][meta['item_pool']]}\n"
               f"**Item Functionality:** {settings_map['item_functionality'][meta['item_functionality']]}"
               ),
        inline=False
    )


def _add_settings_fields(embed, meta, settings_map):
    embed.add_field(
        name='Item Placement',
        value="**Glitches Required:** {logic}\n**Item Placement:** {item_placement}\n**Dungeon Items:** {dungeon_items}\n**Accessibility:** {accessibility}".format(
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


async def _alttpr_embed(seed: ALTTPR, emojis, name, notes, include_settings, tournament):
    settings_map = await seed.randomizer_settings()

    meta = seed.data['spoiler'].get('meta', {})

    embed = discord.Embed(
        title=meta.get('name', REQUESTED_SEED) if not name else name,
        description=html2markdown.convert(
            meta.get('notes', '')) if not notes else notes,
        color=discord.Colour.dark_gold() if tournament else discord.Colour.dark_red(),
        timestamp=datetime.datetime.fromisoformat(seed.data['generated'])
    )

    if include_settings:
        if meta.get('spoilers', 'off') == "mystery":
            _add_mystery_fields(embed, meta)
        elif meta.get('special', False):
            _add_festive_fields(embed, meta, settings_map)
        else:
            _add_settings_fields(embed, meta, settings_map)

    embed.add_field(name=FILE_SELECT_CODE, value=build_file_select_code(
        seed, emojis=emojis), inline=False)

    if not tournament:
        embed.add_field(name='Permalink', value=seed.url, inline=False)

    embed.set_footer(text="Generated", icon_url=_footer_icon(emojis))
    return embed


async def alttpr_embed(seed: ALTTPR, emojis=False, name=False, notes=False, include_settings=True):
    return await _alttpr_embed(seed, emojis, name, notes, include_settings, tournament=False)


async def alttpr_tournament_embed(seed: ALTTPR, emojis=False, name=False, notes=False, include_settings=True):
    return await _alttpr_embed(seed, emojis, name, notes, include_settings, tournament=True)


# --- Door Randomizer (generated locally) ---

def door_embed(seed: AlttprDoor, emojis=False, name=False, notes=False, include_settings=True):
    embed = discord.Embed(
        title=name if name else REQUESTED_SEED,
        description=notes if notes else "Requested Door Randomizer Game.",
        color=discord.Colour.dark_red()
    )

    embed.add_field(
        name=DOOR_RANDOMIZER,
        value="This game was generated using Aerinon's Door Randomizer.",
        inline=False)

    embed.add_field(name=FILE_SELECT_CODE, value=build_file_select_code(
        seed, emojis=emojis), inline=False)

    embed.add_field(name='Permalink', value=seed.url, inline=False)

    if seed.spoilers:
        embed.add_field(name='Spoiler Log', value=seed.spoiler_url, inline=False)
        if seed.attempts > 1:
            embed.add_field(name='Generation Attempts', value=seed.attempts, inline=False)

    embed.add_field(name="Version", value=seed.version)
    embed.set_footer(text="Generated", icon_url=_footer_icon(emojis))
    return embed


def door_tournament_embed(seed: AlttprDoor, emojis=False, name=False, notes=False, include_settings=True):
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_gold()
    )

    embed.add_field(
        name=DOOR_RANDOMIZER,
        value="This game was generated using Aerinon's Door Randomizer.",
        inline=False)

    embed.add_field(name=FILE_SELECT_CODE, value=build_file_select_code(seed, emojis=emojis), inline=False)

    if seed.spoilers:
        embed.add_field(name='Spoiler Log', value=seed.spoiler_url, inline=False)
        if seed.attempts > 1:
            embed.add_field(name='Generation Attempts', value=seed.attempts, inline=False)

    embed.add_field(name="Version", value=seed.version)

    embed.set_footer(text="Generated", icon_url=_footer_icon(emojis))
    return embed


# --- AVIANART ---

def avianart_embed(seed: AVIANART, emojis=False, name=False, notes=False, include_settings=True):
    embed = discord.Embed(
        title=name if name else REQUESTED_SEED,
        description=notes if notes else "Requested Door Randomizer Game.",
        color=discord.Colour.dark_red()
    )

    embed.add_field(
        name='AVIANART',
        value="This game was generated using Hi, I'm Cody's AVIANART generator.",
        inline=False)

    embed.add_field(name='Preset', value=seed.preset, inline=False)
    embed.add_field(name=FILE_SELECT_CODE, value=build_file_select_code(
        seed, emojis=emojis), inline=False)

    embed.add_field(name='Permalink', value=seed.url, inline=False)

    embed.add_field(name="Version", value=seed.version)
    embed.set_footer(text="Generated", icon_url=_footer_icon(emojis))
    return embed


def avianart_tournament_embed(seed: AVIANART, emojis=False, name=False, notes=False, include_settings=True):
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_gold()
    )

    embed.add_field(
        name=DOOR_RANDOMIZER,
        value="This game was generated using Hi, I'm Cody's AVIANART generator.",
        inline=False)

    embed.add_field(name=FILE_SELECT_CODE, value=build_file_select_code(seed, emojis=emojis), inline=False)

    # No spoiler currently for AVIANART, this causes the game to faile to generate.
    # if seed.spoilers:
    #     embed.add_field(name='Spoiler Log', value=seed.spoiler_url, inline=False)
    #     if seed.attempts > 1:
    #         embed.add_field(name='Generation Attempts', value=seed.attempts, inline=False)

    embed.add_field(name="Version", value=seed.version)

    embed.set_footer(text="Generated", icon_url=_footer_icon(emojis))
    return embed


# --- Super Metroid / SMZ3 (samus.link) ---

def sm_embed(seed: smClass, name=REQUESTED_SEED, notes: str = None, emojis=None, include_settings=True):
    if notes is None:
        notes = f"Requested {seed.randomizer.upper()} Randomizer Game."
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_red()
    )

    embed.add_field(name=FILE_SELECT_CODE, value=seed.code, inline=False)
    embed.add_field(name='Permalink', value=seed.url, inline=False)
    embed.set_footer(text="Generated by SahasrahBot")
    return embed


def sm_tournament_embed(seed: smClass, name='Requested Tournament Seed', notes='See notes', emojis=None,
                              include_settings=True):
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_gold()
    )

    embed.add_field(name=FILE_SELECT_CODE, value=seed.code, inline=False)
    embed.set_footer(text="Generated by SahasrahBot")
    return embed


# --- Super Metroid VARIA ---

def smvaria_embed(seed: SuperMetroidVaria):
    embed = discord.Embed(
        title="Generated Super Metroid Varia Game",
        description=f"**Skills preset: **{seed.skills_preset}\n**Settings preset: **{seed.settings_preset}",
        color=discord.Colour.orange(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(
        name="Link",
        value=seed.url,
        inline=False
    )
    if seed.data.get('errorMsg', '') != '':
        embed.add_field(
            name="Warnings",
            value=seed.data.get('errorMsg', ''),
            inline=False
        )
    return embed


# --- Dispatch on seed type ---

_BUILDERS = [
    # (seed class, embed builder, tournament embed builder)
    (ALTTPR, alttpr_embed, alttpr_tournament_embed),
    (AlttprDoor, door_embed, door_tournament_embed),
    (AVIANART, avianart_embed, avianart_tournament_embed),
    (smClass, sm_embed, sm_tournament_embed),
]


async def _built(result) -> discord.Embed:
    """Builders that call alttpr.com are coroutines; the rest return the embed directly."""
    return await result if inspect.isawaitable(result) else result


def _builders_for(seed):
    for cls, embed, tournament_embed in _BUILDERS:
        if isinstance(seed, cls):
            return embed, tournament_embed
    raise TypeError(f"No Discord embed builder for seed type {type(seed).__name__}")


async def seed_embed(seed, **kwargs) -> discord.Embed:
    """The public embed for any generated seed."""
    embed, _ = _builders_for(seed)
    return await _built(embed(seed, **kwargs))


async def seed_tournament_embed(seed, **kwargs) -> discord.Embed:
    """The tournament (staff/player) embed for any generated seed, without the permalink."""
    _, tournament_embed = _builders_for(seed)
    return await _built(tournament_embed(seed, **kwargs))
