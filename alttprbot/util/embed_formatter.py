import discord
import datetime


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
            notes = seed.data['spoiler']['meta']['notes']
        except KeyError:
            notes = ""

    embed = discord.Embed(
        title=name,
        description=notes,
        color=discord.Colour.dark_red())
    embed.add_field(
        name='Item Placement',
        value="Logic: {logic}\nItem Placement: {item_placement}\nDungeon Items: {dungeon_items}\nAccessibility: {accessibility}".format(
            logic=seed.data['spoiler']['meta']['logic'],
            item_placement=seed.data['spoiler']['meta']['item_placement'],
            dungeon_items=seed.data['spoiler']['meta']['dungeon_items'],
            accessibility=seed.data['spoiler']['meta']['accessibility'],
        ),
        inline=True)
    embed.add_field(
        name='Goal',
        value="Goal: {goal}\nOpen Tower: {tower}\nGanon Vulnerable: {crystals}".format(
            goal=seed.data['spoiler']['meta']['goal'],
            tower=seed.data['spoiler']['meta']['entry_crystals_tower'],
            crystals=seed.data['spoiler']['meta']['entry_crystals_ganon'],
        ),
        inline=True)
    embed.add_field(
        name='Gameplay',
        value="World State: {mode}\nEntrance Shuffle: {entrance}\nBoss Shuffle: {boss}\nEnemy Shuffle: {enemy}\nHints: {hints}".format(
            mode=seed.data['spoiler']['meta']['mode'],
            entrance=seed.data['spoiler']['meta']['shuffle'] if seed.data['spoiler']['meta']['shuffle'] else "none",
            boss=seed.data['spoiler']['meta']['enemizer.boss_shuffle'],
            enemy=seed.data['spoiler']['meta']['enemizer.enemy_shuffle'],
            hints=seed.data['spoiler']['meta']['hints']
        ),
        inline=True)
    embed.add_field(
        name='Difficulty',
        value="Swords: {weapons}\nItem Pool: {pool}\nItem Functionality: {functionality}\nEnemy Damage: {damage}\nEnemy Health: {health}".format(
            weapons=seed.data['spoiler']['meta']['weapons'],
            pool=seed.data['spoiler']['meta']['item_pool'],
            functionality=seed.data['spoiler']['meta']['item_functionality'],
            damage=seed.data['spoiler']['meta']['enemizer.enemy_damage'],
            health=seed.data['spoiler']['meta']['enemizer.enemy_health'],
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
