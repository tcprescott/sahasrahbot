"""Discord embed rendering for generated seeds (presentation).

The service tier returns presentation-neutral seed objects
(``alttprbot.services.seedgen.seedclasses``); this module builds the
``discord.Embed`` for each. ``seed_embed`` / ``seed_tournament_embed`` dispatch on
the seed type so callers that handle several randomizers can stay polymorphic
(replacing the old per-class ``seed.embed()`` method dispatch).
"""

import datetime

import discord
import html2markdown

from alttprbot.services.seedgen.seedclasses import (
    ALTTPRSeed,
    AlttprDoorSeed,
    AVIANARTSeed,
    SMSeed,
)

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


def build_file_select_code(seed, emojis=None):
    if emojis:
        emoji_list = list(map(lambda x: str(discord.utils.get(
            emojis, name=emoji_code_map[x])), seed.code))
        return ' '.join(emoji_list) + ' (' + '/'.join(seed.code) + ')'
    else:
        return '/'.join(seed.code)


async def alttpr_embed(seed, emojis=False, name=False, notes=False, include_settings=True):
    settings_map = await seed.randomizer_settings()

    meta = seed.data['spoiler'].get('meta', {})

    embed = discord.Embed(
        title=meta.get('name', 'Requested Seed') if not name else name,
        description=html2markdown.convert(
            meta.get('notes', '')) if not notes else notes,
        color=discord.Colour.dark_red(),
        timestamp=datetime.datetime.fromisoformat(seed.data['generated'])
    )

    if include_settings:
        if meta.get('spoilers', 'off') == "mystery":
            embed.add_field(
                name='Mystery Game',
                value="No meta information is available for this game.",
                inline=False)
            embed.add_field(
                name='Item Placement',
                value=f"**Glitches Required:** {meta['logic']}",
                inline=True)
        else:
            if meta.get('special', False):
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
            else:
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

    embed.add_field(name='File Select Code', value=build_file_select_code(
        seed, emojis=emojis), inline=False)

    embed.add_field(name='Permalink', value=seed.url, inline=False)

    embed.set_footer(text="Generated", icon_url=discord.utils.get(
        emojis, name="SahasrahBot").url)
    return embed


async def alttpr_tournament_embed(seed, emojis=False, name=False, notes=False, include_settings=True):
    settings_map = await seed.randomizer_settings()

    meta = seed.data['spoiler'].get('meta', {})

    embed = discord.Embed(
        title=meta.get('name', 'Requested Seed') if not name else name,
        description=html2markdown.convert(
            meta.get('notes', '')) if not notes else notes,
        color=discord.Colour.dark_gold(),
        timestamp=datetime.datetime.fromisoformat(seed.data['generated'])
    )

    if include_settings:
        if meta.get('spoilers', 'off') == "mystery":
            embed.add_field(
                name='Mystery Game',
                value="No meta information is available for this game.",
                inline=False)
            embed.add_field(
                name='Item Placement',
                value=f"**Glitches Required:** {meta['logic']}",
                inline=True)
        else:
            if meta.get('special', False):
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
            else:
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

    embed.add_field(name='File Select Code', value=build_file_select_code(
        seed, emojis=emojis), inline=False)

    embed.set_footer(text="Generated", icon_url=discord.utils.get(
        emojis, name="SahasrahBot").url)
    return embed


async def alttprdoor_embed(seed, emojis=False, name=False, notes=False, include_settings=True):
    embed = discord.Embed(
        title=name if name else "Requested Seed",
        description=notes if notes else "Requested Door Randomizer Game.",
        color=discord.Colour.dark_red()
    )

    embed.add_field(
        name='Door Randomizer',
        value="This game was generated using Aerinon's Door Randomizer.",
        inline=False)

    embed.add_field(name='File Select Code', value=build_file_select_code(
        seed, emojis=emojis), inline=False)

    embed.add_field(name='Permalink', value=seed.url, inline=False)

    if seed.spoilers:
        embed.add_field(name='Spoiler Log', value=seed.spoiler_url, inline=False)
        if seed.attempts > 1:
            embed.add_field(name='Generation Attempts', value=seed.attempts, inline=False)

    embed.add_field(name="Version", value=seed.version)
    embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
    return embed


async def alttprdoor_tournament_embed(seed, emojis=False, name=False, notes=False, include_settings=True):
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_gold()
    )

    embed.add_field(
        name='Door Randomizer',
        value="This game was generated using Aerinon's Door Randomizer.",
        inline=False)

    embed.add_field(name='File Select Code', value=build_file_select_code(seed, emojis=emojis), inline=False)

    if seed.spoilers:
        embed.add_field(name='Spoiler Log', value=seed.spoiler_url, inline=False)
        if seed.attempts > 1:
            embed.add_field(name='Generation Attempts', value=seed.attempts, inline=False)

    embed.add_field(name="Version", value=seed.version)

    embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
    return embed


async def avianart_embed(seed, emojis=False, name=False, notes=False):
    embed = discord.Embed(
        title=name if name else "Requested Seed",
        description=notes if notes else "Requested Door Randomizer Game.",
        color=discord.Colour.dark_red()
    )

    embed.add_field(
        name='AVIANART',
        value="This game was generated using Hi, I'm Cody's AVIANART generator.",
        inline=False)

    embed.add_field(name='Preset', value=seed.preset, inline=False)
    embed.add_field(name='File Select Code', value=build_file_select_code(
        seed, emojis=emojis), inline=False)

    embed.add_field(name='Permalink', value=seed.url, inline=False)

    embed.add_field(name="Version", value=seed.version)
    embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
    return embed


async def avianart_tournament_embed(seed, emojis=False, name=False, notes=False, include_settings=True):
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_gold()
    )

    embed.add_field(
        name='Door Randomizer',
        value="This game was generated using Hi, I'm Cody's AVIANART generator.",
        inline=False)

    embed.add_field(name='File Select Code', value=build_file_select_code(seed, emojis=emojis), inline=False)

    # No spoiler currently for AVIANART, this causes the game to faile to generate.
    # if seed.spoilers:
    #     embed.add_field(name='Spoiler Log', value=seed.spoiler_url, inline=False)
    #     if seed.attempts > 1:
    #         embed.add_field(name='Generation Attempts', value=seed.attempts, inline=False)

    embed.add_field(name="Version", value=seed.version)

    embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
    return embed


async def sm_embed(seed, name="Requested Seed", notes: str = None, emojis=None, include_settings=True):
    if notes is None:
        notes = f"Requested {seed.randomizer.upper()} Randomizer Game."
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_red()
    )

    embed.add_field(name='File Select Code', value=seed.code, inline=False)
    embed.add_field(name='Permalink', value=seed.url, inline=False)
    embed.set_footer(text="Generated by SahasrahBot")
    return embed


async def sm_tournament_embed(seed, name='Requested Tournament Seed', notes='See notes', emojis=None,
                              include_settings=True):
    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_gold()
    )

    embed.add_field(name='File Select Code', value=seed.code, inline=False)
    embed.set_footer(text="Generated by SahasrahBot")
    return embed


def smvaria_embed(seed):
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


_EMBED_DISPATCH = (
    (ALTTPRSeed, alttpr_embed),
    (AlttprDoorSeed, alttprdoor_embed),
    (AVIANARTSeed, avianart_embed),
    (SMSeed, sm_embed),
)

_TOURNAMENT_EMBED_DISPATCH = (
    (ALTTPRSeed, alttpr_tournament_embed),
    (AlttprDoorSeed, alttprdoor_tournament_embed),
    (AVIANARTSeed, avianart_tournament_embed),
    (SMSeed, sm_tournament_embed),
)


async def seed_embed(seed, **kwargs):
    """Build the standard seed embed, dispatching on the seed's randomizer type."""
    for seed_cls, builder in _EMBED_DISPATCH:
        if isinstance(seed, seed_cls):
            return await builder(seed, **kwargs)
    raise TypeError(f"No embed builder registered for seed type {type(seed).__name__}")


async def seed_tournament_embed(seed, **kwargs):
    """Build the tournament seed embed, dispatching on the seed's randomizer type."""
    for seed_cls, builder in _TOURNAMENT_EMBED_DISPATCH:
        if isinstance(seed, seed_cls):
            return await builder(seed, **kwargs)
    raise TypeError(f"No tournament embed builder registered for seed type {type(seed).__name__}")
