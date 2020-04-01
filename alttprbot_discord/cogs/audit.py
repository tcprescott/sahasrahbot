import datetime

import discord
from discord.ext import commands

from alttprbot.database import audit, config


class Audit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.clean_history.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.id == self.bot.user.id:
            return
        if message.guild is None:
            await record_message(message)
            return
        if await config.get(message.guild.id, 'AuditLogging') == 'true':
            await record_message(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)

        # ignore these channels for reasons
        if channel and channel.id in [694710452478803968, 694710286455930911]:
            return

        if payload.message_id == self.bot.user.id:
            return
        if await config.get(guild.id, 'AuditLogging') == 'true':
            audit_channel_id = await config.get(guild.id, 'AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_delete(guild, channel, payload.message_id)
                audit_channel = discord.utils.get(guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)
                await audit.set_deleted(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        if payload.message_id == self.bot.user.id:
            return
        if await config.get(guild.id, 'AuditLogging') == 'true':
            audit_channel_id = await config.get(guild.id, 'AuditLogChannel')
            for message_id in payload.message_ids:
                if audit_channel_id:
                    embed = await audit_embed_delete(guild, channel, message_id)
                    audit_channel = discord.utils.get(guild.channels, id=int(audit_channel_id))

                    await audit_channel.send(embed=embed)
                    await audit.set_deleted(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        if isinstance(channel, discord.DMChannel):
            return
        message = await channel.fetch_message(payload.message_id)
        if message.author.id == self.bot.user.id:
            return
        if await config.get(message.guild.id, 'AuditLogging') == 'true':
            old_message = await audit.get_cached_messages(message.id)
            if old_message[-1]['content'] == message.content:
                return
            audit_channel_id = await config.get(message.guild.id, 'AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_edit(old_message, message)
                audit_channel = discord.utils.get(message.guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)

            await record_message(message)

    # @commands.Cog.listener()
    # async def on_reaction_clear(self, message, reactions):
    #     if await config.get(message.guild.id, 'AuditLogging') == 'true':
    #         print("cleared reactions")

    # @commands.Cog.listener()
    # async def on_guild_channel_delete(self, channel):
    #     if await config.get(channel.guild.id, 'AuditLogging') == 'true':
    #         print("channel delete")

    # @commands.Cog.listener()
    # async def on_guild_channel_create(self, channel):
    #     if await config.get(channel.guild.id, 'AuditLogging') == 'true':
    #         print("channel create")

    # @commands.Cog.listener()
    # async def on_guild_channel_update(self, before, after):
    #     if await config.get(after.guild.id, 'AuditLogging') == 'true':
    #         print("channel update")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild is None:
            return
        if await config.get(member.guild.id, 'AuditLogging') == 'true':
            audit_channel_id = await config.get(member.guild.id, 'AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_member_joined(member)
                audit_channel = discord.utils.get(member.guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild is None:
            return
        if await config.get(member.guild.id, 'AuditLogging') == 'true':
            audit_channel_id = await config.get(member.guild.id, 'AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_member_left(member)
                audit_channel = discord.utils.get(member.guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)

    # # role membership
    # # display_name
    # @commands.Cog.listener()
    # async def on_member_update(self, before, after):
    #     if await config.get(after.guild.id, 'AuditLogging') == 'true':
    #         print("member update")

    # @commands.Cog.listener()
    # async def on_user_update(self, before, after):
    #     if await config.get(after.guild.id, 'AuditLogging') == 'true':
    #         print("user update")

    # @commands.Cog.listener()
    # async def on_guild_role_create(self, role):
    #     if await config.get(role.guild.id, 'AuditLogging') == 'true':
    #         print("role create")

    # @commands.Cog.listener()
    # async def on_guild_role_delete(self, role):
    #     if await config.get(role.guild.id, 'AuditLogging') == 'true':
    #         print("role delete")

    # @commands.Cog.listener()
    # async def on_guild_role_update(self, before, after):
    #     if await config.get(after.guild.id, 'AuditLogging') == 'true':
    #         print("role update")

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):
    #     if await config.get(after.guild.id, 'AuditLogging') == 'true':
    #         print("voice state change")

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if guild is None:
            return
        if await config.get(guild.id, 'AuditLogging') == 'true':
            audit_channel_id = await config.get(user.guild.id, 'AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_member_banned(user)
                audit_channel = discord.utils.get(user.guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)

    # @commands.Cog.listener()
    # async def on_member_unban(self, guild, user):
    #     if await config.get(guild.id, 'AuditLogging') == 'true':
    #         print("member unban")

    # @tasks.loop(minutes=1, reconnect=True)
    # async def clean_history(self):
    #     print('history cleaned')
    #     await audit.clean_history()

# async def audit_embed_member_joined(member):
#     embed = discord.Embed(
#         title="Member Joined",
#         description=f"{member.mention} {member.name}#{member.discriminator}",
#         color=discord.Colour.green(),
#         timestamp=datetime.datetime.now()
#     )
#     embed.set_thumbnail(url=member.avatar_url)
#     return embed

async def audit_embed_member_joined(member):
    embed = discord.Embed(
        title="Member Joined",
        description=f"{member.mention} {member.name}#{member.discriminator}",
        color=discord.Colour.green(),
        timestamp=datetime.datetime.now()
    )
    embed.set_thumbnail(url=member.avatar_url)
    return embed

async def audit_embed_member_left(member):
    embed = discord.Embed(
        title="Member Left",
        description=f"{member.mention} {member.name}#{member.discriminator}",
        color=discord.Colour.red(),
        timestamp=datetime.datetime.now()
    )
    embed.set_thumbnail(url=member.avatar_url)
    return embed

async def audit_embed_member_banned(member):
    embed = discord.Embed(
        title="Member Banned",
        description=f"{member.mention} {member.name}#{member.discriminator}",
        color=discord.Colour.red(),
        timestamp=datetime.datetime.now()
    )
    embed.set_thumbnail(url=member.avatar_url)
    return embed

async def audit_embed_edit(old_message, message):
    if not old_message:
        old_content = '??? err unknown ???'
    else:
        old_content = old_message[-1]['content']
    
    old_content = '*empty*' if old_content == '' else old_content
    new_content = '*empty*' if message.content == '' else message.content

    embed = discord.Embed(
        title="Message Edited",
        description=f"**A message from {message.author.mention} was edited in {message.channel.mention}.** [Jump to Message]({message.jump_url})",
        color=discord.Colour.dark_orange(),
        timestamp=datetime.datetime.now()
    )

    embed.add_field(name='Old Message', value=old_content[:1000] + ('..' if len(old_content) > 1000 else ''), inline=False)
    embed.add_field(name='New Message', value=new_content[:1000] + ('..' if len(new_content) > 1000 else ''))
    embed.set_footer(text="Logged at")

    return embed

async def audit_embed_delete(guild, channel, message_id, bulk=False):
    old_message = await audit.get_cached_messages(message_id)
    if old_message is None:
        author = None
        old_content = '*unknown*'
        old_attachment_url = None
        original_timestamp = '*unknown*'
    else:
        author = guild.get_member(int(old_message[-1]['user_id']))
        old_content = old_message[-1]['content']
        old_attachment_url = old_message[-1]['attachment']
        original_timestamp = f"{old_message[0]['message_date']} UTC"
    
    old_content = '*empty*' if old_content == '' else old_content

    embed = discord.Embed(
        title="Bulk Message Deleted" if bulk else "Message Deleted",
        description=f"**Message sent by {'unknown' if author is None else author.mention} was deleted in {channel.mention}.**",
        color=discord.Colour.dark_red(),
        timestamp=datetime.datetime.now()
    )

    embed.add_field(name='Old Message', value=old_content[:1500] + ('..' if len(old_content) > 1500 else ''), inline=False)
    if old_attachment_url:
        embed.add_field(name='Old Attachment', value=old_attachment_url, inline=False)
    embed.add_field(name='Message Timestamp', value=original_timestamp, inline=False)
    embed.set_footer(text="Logged at")

    return embed

async def record_message(message):
    await audit.insert_message(
        guild_id=message.guild.id if message.guild else 0,
        message_id=message.id,
        user_id=message.author.id,
        channel_id=message.channel.id,
        message_date=message.created_at,
        content=message.content,
        attachment=message.attachments[0].url if message.attachments else None
    )

def setup(bot):
    bot.add_cog(Audit(bot))
