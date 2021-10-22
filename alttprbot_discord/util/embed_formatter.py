import datetime

import discord


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
            description=item['description'], channel=channel.mention, messagelink=message.jump_url,
            botmanaged='something')
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
        color=discord.Colour.green(),
        timestamp=datetime.datetime.now()
    )
    value = ''
    for role in roles:
        value = value + '{emoji} `{name}`: {description}\n'.format(
            emoji=role['emoji'],
            name=role['name'],
            description=role['description']
        )
    embed.add_field(name='Roles', value=value, inline=False)
    embed.set_footer(text=group['id'])
    return embed
