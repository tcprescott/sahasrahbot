import discord
import datetime
from html.parser import HTMLParser

def permissions(ctx, permissions):
    embed = discord.Embed(
        title="Server Permissions",
        description="List of permissions and assigned roles for those permissions.",
        color=discord.Colour.green())
    permdict = {}
    for permission in permissions:
        role = discord.utils.get(
            ctx.guild.roles,
            id=permission['role_id']).name
        permdict.setdefault(permission['permission'], []).append(role)
    for perm in permdict:
        embed.add_field(
            name=perm,
            value='\n'.join(
                permdict.get(perm)),
            inline=False)
    return embed


def config(ctx, configdict):
    embed = discord.Embed(
        title="Server Configuration",
        description="List of configuration parameters for this server.",
        color=discord.Colour.teal())
    for item in configdict:
        embed.add_field(name=item['parameter'], value=item['value'])
    return embed


async def reaction_group_list(ctx, reaction_groups):
    embed = discord.Embed(
        title="Server Reaction Groups",
        description="List of server reaction groups.",
        color=discord.Colour.gold())
    for item in reaction_groups:
        channel = ctx.guild.get_channel(item['channel_id'])
        message = await channel.fetch_message(item['message_id'])
        name = '{id}: {name}'.format(
            id=item['id'],
            name=item['name']
        )
        value = 'Description: {description}\n\nChannel: {channel}\nMessage Link: {messagelink}\nBot Managed: {botmanaged}'.format(
            description=item['description'], channel=channel.mention, messagelink=message.jump_url, botmanaged='something')
        embed.add_field(name=name, value=value, inline=False)
    return embed


def reaction_role_list(ctx, reaction_roles):
    embed = discord.Embed(
        title="Reaction Roles for Group",
        description="List of reaction roles for specified group.",
        color=discord.Colour.gold())
    for item in reaction_roles:
        role_obj = ctx.guild.get_role(item['role_id'])
        name = '{id}: {name}'.format(
            id=item['id'],
            name=item['name']
        )
        value = 'Role: {role}\nDescription: {description}\nEmoji: {emoji}\nProtected: {protected}'.format(
            role=role_obj, description=item['description'], emoji=item['emoji'], protected=bool(
                item['protect_mentions']))
        embed.add_field(name=name, value=value, inline=False)
    return embed


def reaction_menu(ctx, group, roles):
    embed = discord.Embed(
        title=group['name'],
        description=group['description'],
        color=discord.Colour.green())
    value = ''
    for role in roles:
        value = value + '{emoji} `{name}`: {description}\n'.format(
            emoji=role['emoji'],
            name=role['name'],
            description=role['description']
        )
    embed.add_field(name='Roles', value=value, inline=False)
    embed.set_footer(text='id: {id} - last updated {date}'.format(
        id=group['id'],
        date=datetime.datetime.now()
    ))
    return embed


async def seed_embed(seed, emojis=False, name=False, notes=False):
    if not name:
        try:
            name = seed.data['spoiler']['meta']['name']
        except KeyError:
            name = 'Requested Seed'

    if not notes:
        try:
            notes = strip_tags(seed.data['spoiler']['meta']['notes'])
        except KeyError:
            notes = ""

    settings_map = await seed.randomizer_settings()

    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_red())

    if 'mystery' in seed.data['spoiler']['meta'] and seed.data['spoiler']['meta']['mystery']:
        embed.add_field(
            name='Mystery Game',
            value="No meta information is available for this game.",
            inline=False)
    else:
        embed.add_field(
            name='Item Placement',
            value="**Glitches Required:** {logic}\n**Item Placement:** {item_placement}\n**Dungeon Items:** {dungeon_items}\n**Accessibility:** {accessibility}".format(
                logic=seed.data['spoiler']['meta']['logic'],
                item_placement=settings_map['item_placement'][seed.data['spoiler']['meta']['item_placement']],
                dungeon_items=settings_map['dungeon_items'][seed.data['spoiler']['meta']['dungeon_items']],
                accessibility=settings_map['accessibility'][seed.data['spoiler']['meta']['accessibility']],
            ),
            inline=True)

        embed.add_field(
            name='Goal',
            value="**Goal:** {goal}\n**Open Tower:** {tower}\n**Ganon Vulnerable:** {ganon}".format(
                goal=settings_map['goals'][seed.data['spoiler']['meta']['goal']],
                tower=seed.data['spoiler']['meta']['entry_crystals_tower'],
                ganon=seed.data['spoiler']['meta']['entry_crystals_ganon'],
            ),
            inline=True)
        embed.add_field(
            name='Gameplay',
            value="**World State:** {mode}\n**Entrance Shuffle:** {entrance}\n**Boss Shuffle:** {boss}\n**Enemy Shuffle:** {enemy}\n**Hints:** {hints}".format(
                mode=settings_map['world_state'][seed.data['spoiler']['meta']['mode']],
                entrance="None" if not 'shuffle' in seed.data['spoiler']['meta'] else settings_map['entrance_shuffle'][seed.data['spoiler']['meta']['shuffle']],
                boss=settings_map['boss_shuffle'][seed.data['spoiler']['meta']['enemizer.boss_shuffle']],
                enemy=settings_map['enemy_shuffle'][seed.data['spoiler']['meta']['enemizer.enemy_shuffle']],
                hints=seed.data['spoiler']['meta']['hints']
            ),
            inline=True)
        embed.add_field(
            name='Difficulty',
            value="**Swords:** {weapons}\n**Item Pool:** {pool}\n**Item Functionality:** {functionality}\n**Enemy Damage:** {damage}\n**Enemy Health:** {health}".format(
                weapons=settings_map['weapons'][seed.data['spoiler']['meta']['weapons']],
                pool=settings_map['item_pool'][seed.data['spoiler']['meta']['item_pool']],
                functionality=settings_map['item_functionality'][seed.data['spoiler']['meta']['item_functionality']],
                damage=settings_map['enemy_damage'][seed.data['spoiler']['meta']['enemizer.enemy_damage']],
                health=settings_map['enemy_health'][seed.data['spoiler']['meta']['enemizer.enemy_health']],
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
        code = await seed.code()
        c = list(map(lambda x: str(discord.utils.get(
            emojis, name=emoji_code_map[x])), code))
        embed.add_field(name='File Select Code', value=' '.join(
            c) + ' (' + '/'.join(code) + ')', inline=False)
    else:
        code = await seed.code()
        embed.add_field(
            name='File Select Code',
            value='/'.join(code),
            inline=False)

    embed.add_field(name='Permalink', value=seed.url, inline=False)
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