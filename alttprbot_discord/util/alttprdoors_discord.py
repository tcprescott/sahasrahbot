import discord

from alttprbot.alttprgen.randomizer.alttprdoor import AlttprDoor

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


class AlttprDoorDiscord(AlttprDoor):
    def __init__(self, *args, **kwargs):
        super(AlttprDoorDiscord, self).__init__(*args, **kwargs)

    @property
    def generated_goal(self):
        return "door randomizer"

    async def embed(self, emojis=False, name=False, notes=False, include_settings=True):
        embed = discord.Embed(
            title=name if name else "Requested Seed",
            description=notes if notes else "Requested Door Randomizer Game.",
            color=discord.Colour.dark_red()
        )

        embed.add_field(
            name='Door Randomizer',
            value="This game was generated using Aerinon's Door Randomizer.",
            inline=False)

        embed.add_field(name='File Select Code', value=self.build_file_select_code(
            emojis=emojis), inline=False)

        embed.add_field(name='Permalink', value=self.url, inline=False)

        if self.spoilers:
            embed.add_field(name='Spoiler Log', value=self.spoiler_url, inline=False)
            if self.attempts > 1:
                embed.add_field(name='Generation Attempts', value=self.attempts, inline=False)

        embed.add_field(name="Version", value=self.version)
        embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
        return embed

    async def tournament_embed(self, emojis=False, name=False, notes=False, include_settings=True):
        embed = discord.Embed(
            title=name,
            description=notes,
            color=discord.Colour.dark_gold()
        )

        embed.add_field(
            name='Door Randomizer',
            value="This game was generated using Aerinon's Door Randomizer.",
            inline=False)

        embed.add_field(name='File Select Code', value=self.build_file_select_code(emojis=emojis), inline=False)

        if self.spoilers:
            embed.add_field(name='Spoiler Log', value=self.spoiler_url, inline=False)
            if self.attempts > 1:
                embed.add_field(name='Generation Attempts', value=self.attempts, inline=False)

        embed.add_field(name="Version", value=self.version)

        embed.set_footer(text="Generated", icon_url=discord.utils.get(emojis, name="SahasrahBot").url)
        return embed

    def build_file_select_code(self, emojis=None):
        if emojis:
            emoji_list = list(map(lambda x: str(discord.utils.get(
                emojis, name=emoji_code_map[x])), self.code))
            return ' '.join(emoji_list) + ' (' + '/'.join(self.code) + ')'
        else:
            return '/'.join(self.code)
