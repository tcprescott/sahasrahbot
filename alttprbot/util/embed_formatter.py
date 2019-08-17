import discord
import datetime

def permissions(ctx, permissions):
    embed = discord.Embed(title="Server Permissions", description="List of permissions and assigned roles for those permissions.", color=discord.Colour.green())
    permdict = {}
    for permission in permissions:
        role = discord.utils.get(ctx.guild.roles, id=permission['role_id']).name
        permdict.setdefault(permission['permission'], []).append(role)
    for perm in permdict:
        embed.add_field(name=perm, value='\n'.join(permdict.get(perm)), inline=False)
    return embed

def config(ctx, configdict):
    embed = discord.Embed(title="Server Configuration", description="List of configuration parameters for this server.", color=discord.Colour.teal())
    for item in configdict:
        embed.add_field(name=item['parameter'], value=item['value'])
    return embed

async def reaction_group_list(ctx, reaction_groups):
    embed = discord.Embed(title="Server Reaction Groups", description="List of server reaction groups.", color=discord.Colour.gold())
    for item in reaction_groups:
        channel = ctx.guild.get_channel(item['channel_id'])
        message = await channel.fetch_message(item['message_id'])
        name = '{id}: {name}'.format(
            id=item['id'],
            name=item['name']
        )
        value = 'Description: {description}\n\nChannel: {channel}\nMessage Link: {messagelink}\nBot Managed: {botmanaged}'.format(
                description = item['description'],
                channel = channel.mention,
                messagelink = message.jump_url,
                botmanaged = 'something'
            )
        embed.add_field(name=name, value=value, inline=False)
    return embed

def reaction_role_list(ctx, reaction_roles):
    embed = discord.Embed(title="Reaction Roles for Group", description="List of reaction roles for specified group.", color=discord.Colour.gold())
    for item in reaction_roles:
        role_obj = ctx.guild.get_role(item['role_id'])
        name = '{id}: {name}'.format(
            id=item['id'],
            name=item['name']
        )
        value = 'Role: {role}\nDescription: {description}\nEmoji: {emoji}\nProtected: {protected}'.format(
                role = role_obj,
                description = item['description'],
                emoji = item['emoji'],
                protected = bool(item['protect_mentions'])
            )
        embed.add_field(name=name, value=value, inline=False)
    return embed

def reaction_menu(ctx, group, roles):
    embed = discord.Embed(title=group['name'], description=group['description'], color=discord.Colour.green())
    value = ''
    for role in roles:
        value = value + '{emoji} `{name}`: {description}\n'.format(
                emoji = role['emoji'],
                name = role['name'],
                description = role['description']
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
            notes = seed.data['spoiler']['meta']['notes']
        except KeyError:
            notes = ""

    embed = discord.Embed(title=name, description=notes, color=discord.Colour.dark_red())
    embed.add_field(name='Logic', value=seed.data['spoiler']['meta']['logic'], inline=True)
    embed.add_field(name='Difficulty', value=seed.data['spoiler']['meta']['difficulty'], inline=True)
    embed.add_field(name='Variation', value=seed.data['spoiler']['meta']['variation'], inline=True)
    embed.add_field(name='State', value=seed.data['spoiler']['meta']['mode'], inline=True)

    try:
        embed.add_field(name='Swords', value=seed.data['spoiler']['meta']['weapons'], inline=True)
    except KeyError:
        pass

    try:
        embed.add_field(name='Shuffle', value=seed.data['spoiler']['meta']['shuffle'], inline=True)
    except KeyError:
        pass

    embed.add_field(name='Goal', value=seed.data['spoiler']['meta']['goal'], inline=True)

    try:
        embed.add_field(name='Enemizer Enemy Shuffle', value=seed.data['spoiler']['meta']['enemizer_enemy'], inline=True)
    except KeyError:
        try:
            if seed.settings and seed.settings['enemizer']: embed.add_field(name='Enemizer Enemy Shuffle', value=seed.settings['enemizer']['enemy'], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Boss Shuffle', value=seed.data['spoiler']['meta']['enemizer_bosses'], inline=True)
    except KeyError:
        try:
            if seed.settings and seed.settings['enemizer']: embed.add_field(name='Enemizer Boss Shuffle', value=seed.settings['enemizer']['bosses'], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Pot Shuffle', value=seed.data['spoiler']['meta']['enemizer_pot_shuffle'], inline=True)
    except KeyError:
        try:
            if seed.settings and seed.settings['enemizer']: embed.add_field(name='Enemizer Pot Shuffle', value=seed.settings['enemizer']['pot_shuffle'], inline=True)
        except KeyError:
            pass

    healthmap = {
        0: 'Default',
        1: 'Easy (1-4 hp)',
        2: 'Normal (2-15 hp)',
        3: 'Hard (2-30 hp)',
        4: 'Brick Wall (4-50 hp)'
    }
    try:
        embed.add_field(name='Enemizer Enemy Health', value=healthmap[seed.data['spoiler']['meta']['enemizer_enemy_health']], inline=True)
    except KeyError:
        try:
            if seed.settings and seed.settings['enemizer']: embed.add_field(name='Enemizer Enemy Health', value=healthmap[seed.settings['enemizer']['enemy_health']], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Enemy Damage', value=seed.data['spoiler']['meta']['enemizer_enemy_damage'], inline=True)
    except KeyError:
        try:
            if seed.settings and seed.settings['enemizer']: embed.add_field(name='Enemizer Enemy Damage', value=seed.settings['enemizer']['enemy_damage'], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Palette Shuffle', value=seed.data['spoiler']['meta']['enemizer_palette_shuffle'], inline=True)
    except KeyError:
        try:
            if seed.settings and seed.settings['enemizer']: embed.add_field(name='Enemizer Palette Shuffle', value=seed.settings['enemizer']['palette_shuffle'], inline=True)
        except KeyError:
            pass

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
        c=list(map(lambda x: str(discord.utils.get(emojis, name=emoji_code_map[x])), code))
        embed.add_field(name='File Select Code', value=' '.join(c) + ' (' + '/'.join(code) + ')', inline=False)
    else:
        code = await seed.code()
        embed.add_field(name='File Select Code', value='/'.join(code), inline=False)

    embed.add_field(name='Permalink', value=seed.url, inline=False)
    return embed
