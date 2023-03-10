import csv
import datetime
import io
from contextlib import closing

import discord
from alttprbot import models
from discord.ext import commands, tasks


class Audit(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.clean_history.start()

    @tasks.loop(hours=24, reconnect=True)
    async def clean_history(self):
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        await models.AuditMessages.filter(message_date__lte=thirty_days_ago).delete()

    @clean_history.before_loop
    async def before_clean_history(self):
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def messagehistory(self, ctx, member: discord.Member, limit=500):
        messages = await models.AuditMessages.filter(guild_id=ctx.guild.id, user_id=member.id).limit(limit).values()

        fields = ['message_date', 'content', 'attachment', 'deleted']
        with closing(io.StringIO()) as sio:
            writer = csv.DictWriter(sio, fieldnames=fields)
            writer.writeheader()
            writer.writerows(messages)
            sio.seek(0)
            discord_file = discord.File(
                fp=sio, filename=f"{member.id}_history.csv")
            await ctx.reply(file=discord_file)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def deletedhistory(self, ctx, member: discord.Member, limit=500):
        messages = await models.AuditMessages.filter(guild_id=ctx.guild.id, user_id=member.id, deleted=1).limit(limit).values()

        fields = ['message_date', 'content', 'attachment', 'deleted']
        with closing(io.StringIO()) as sio:
            writer = csv.DictWriter(sio, fieldnames=fields)
            writer.writeheader()
            writer.writerows(messages)
            sio.seek(0)
            discord_file = discord.File(
                fp=sio, filename=f"{member.id}_deleted.csv")
            await ctx.reply(file=discord_file)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            await record_message(message)
            return
        if message.channel == 606873327839215616:
            return

        await record_message(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)

        # message = await channel.fetch_message(payload.message_id)
        # if message.author.bot:
        #     return

        audit_channel_id = await guild.config_get('AuditLogChannel')
        if audit_channel_id:
            embed = await audit_embed_delete(guild, channel, payload.message_id)
            audit_channel = discord.utils.get(
                guild.channels, id=int(audit_channel_id))

            await audit_channel.send(embed=embed)

            cached_messages = await models.AuditMessages.filter(message_id=payload.message_id)
            if cached_messages:
                for msg in cached_messages:
                    msg.deleted = 1
                    await msg.save(update_fields=['deleted'])

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)

        # message = await channel.fetch_message(payload.message_id)
        # if message.author.bot:
        #     return

        audit_channel_id = await guild.config_get('AuditLogChannel')
        if not audit_channel_id:
            return

        audit_channel = discord.utils.get(guild.channels, id=int(audit_channel_id))

        for message_id in payload.message_ids:
            embed = await audit_embed_delete(guild, channel, message_id)

            await audit_channel.send(embed=embed)
            cached_message = await models.AuditMessages.get(message_id=message_id)
            cached_message.deleted = 1
            await cached_message.save()

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        if isinstance(channel, discord.DMChannel):
            return

        # ignore these channels for reasons
        if channel and channel.id in [694710452478803968, 694710286455930911, 606873327839215616]:
            return

        message = await channel.fetch_message(payload.message_id)
        if message.author.bot:
            return

        old_message = await models.AuditMessages.filter(message_id=message.id).order_by('id').values()
        if old_message and old_message[-1]['content'] == message.content:
            return
        audit_channel_id = await message.guild.config_get('AuditLogChannel')
        if audit_channel_id:
            embed = await audit_embed_edit(old_message, message)
            audit_channel = discord.utils.get(
                message.guild.channels, id=int(audit_channel_id))

            await audit_channel.send(embed=embed)

        await record_message(message)

    # @commands.Cog.listener()
    # async def on_reaction_clear(self, message, reactions):
    #     if await message.guild.config_get('AuditLogging') == 'true':
    #         logging.info("cleared reactions")

    # @commands.Cog.listener()
    # async def on_guild_channel_delete(self, channel):
    #     if await channel.guild.config_get('AuditLogging') == 'true':
    #         logging.info("channel delete")

    # @commands.Cog.listener()
    # async def on_guild_channel_create(self, channel):
    #     if await channel.guild.config_get('AuditLogging') == 'true':
    #         logging.info("channel create")

    # @commands.Cog.listener()
    # async def on_guild_channel_update(self, before, after):
    #     if await after.guild.config_get('AuditLogging') == 'true':
    #         logging.info("channel update")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild is None:
            return
        if await member.guild.config_get('AuditLogging') == 'true':
            audit_channel_id = await member.guild.config_get('AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_member_joined(member)
                audit_channel = discord.utils.get(
                    member.guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild is None:
            return
        if await member.guild.config_get('AuditLogging') == 'true':
            audit_channel_id = await member.guild.config_get('AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_member_left(member)
                audit_channel = discord.utils.get(
                    member.guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)

    # # role membership
    # # display_name
    # @commands.Cog.listener()
    # async def on_member_update(self, before, after):
    #     if await after.guild.config_get('AuditLogging') == 'true':
    #         logging.info("member update")

    # @commands.Cog.listener()
    # async def on_user_update(self, before, after):
    #     if await after.guild.config_get('AuditLogging') == 'true':
    #         logging.info("user update")

    # @commands.Cog.listener()
    # async def on_guild_role_create(self, role):
    #     if await role.guild.config_get('AuditLogging') == 'true':
    #         logging.info("role create")

    # @commands.Cog.listener()
    # async def on_guild_role_delete(self, role):
    #     if await role.guild.config_get('AuditLogging') == 'true':
    #         logging.info("role delete")

    # @commands.Cog.listener()
    # async def on_guild_role_update(self, before, after):
    #     if await after.guild.config_get('AuditLogging') == 'true':
    #         logging.info("role update")

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):
    #     if await after.guild.config_get('AuditLogging') == 'true':
    #         logging.info("voice state change")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user):
        if guild is None:
            return
        if await guild.config_get('AuditLogging') == 'true':
            audit_channel_id = await guild.config_get('AuditLogChannel')
            if audit_channel_id:
                embed = await audit_embed_member_banned(user)
                audit_channel = discord.utils.get(guild.channels, id=int(audit_channel_id))

                await audit_channel.send(embed=embed)

    # @commands.Cog.listener()
    # async def on_member_unban(self, guild, user):
    #     if await guild.config_get('AuditLogging') == 'true':
    #         logging.info("member unban")

    # @tasks.loop(minutes=1, reconnect=True)
    # async def clean_history(self):
    #     logging.info('history cleaned')
    #     await audit.clean_history()

# async def audit_embed_member_joined(member):
#     embed = discord.Embed(
#         title="Member Joined",
#         description=f"{member.mention} {member.name}#{member.discriminator}",
#         color=discord.Colour.green(),
#         timestamp=discord.utils.utcnow()
#     )
#     if member.avatar:
#         embed.set_thumbnail(url=member.avatar.url)
#     return embed


async def audit_embed_member_joined(member):
    embed = discord.Embed(
        title="Member Joined",
        description=f"{member.mention} {member.name}#{member.discriminator}",
        color=discord.Colour.green(),
        timestamp=discord.utils.utcnow()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    return embed


async def audit_embed_member_left(member):
    embed = discord.Embed(
        title="Member Left",
        description=f"{member.mention} {member.name}#{member.discriminator}",
        color=discord.Colour.red(),
        timestamp=discord.utils.utcnow()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    return embed


async def audit_embed_member_banned(member):
    embed = discord.Embed(
        title="Member Banned",
        description=f"{member.mention} {member.name}#{member.discriminator}",
        color=discord.Colour.red(),
        timestamp=discord.utils.utcnow()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
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
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(name='Old Message', value=old_content[:1000] + (
        '..' if len(old_content) > 1000 else ''), inline=False)
    embed.add_field(name='New Message',
                    value=new_content[:1000] + ('..' if len(new_content) > 1000 else ''))
    embed.set_footer(text="Logged at")

    return embed


async def audit_embed_delete(guild: discord.Guild, channel, message_id, bulk=False):
    old_message = await models.AuditMessages.filter(message_id=message_id).order_by('id').values()
    if old_message is None:
        author = None
        old_content = '*unknown*'
        old_attachment_url = None
        original_timestamp = '*unknown*'
    else:
        if guild.chunked is False:
            await guild.chunk(cache=True)
        author = guild.get_member(int(old_message[-1]['user_id']))
        old_content = old_message[-1]['content']
        old_attachment_url = old_message[-1]['attachment']
        original_timestamp = f"{old_message[0]['message_date']} UTC"

    old_content = '*empty*' if old_content == '' else old_content

    embed = discord.Embed(
        title="Bulk Message Deleted" if bulk else "Message Deleted",
        description=f"**Message sent by {'unknown' if author is None else author.mention} was deleted in {channel.mention}.**",
        color=discord.Colour.dark_red(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(name='Old Message', value=old_content[:1020] + (
        '...' if len(old_content) > 1020 else ''), inline=False)
    if old_attachment_url:
        embed.add_field(name='Old Attachment',
                        value=old_attachment_url, inline=False)
    embed.add_field(name='Message Timestamp',
                    value=original_timestamp, inline=False)
    embed.set_footer(text="Logged at")

    return embed


async def record_message(message):
    await models.AuditMessages.create(
        guild_id=message.guild.id if message.guild else 0,
        message_id=message.id,
        user_id=message.author.id,
        channel_id=message.channel.id,
        message_date=message.created_at,
        content=message.content,
        attachment=message.attachments[0].url if message.attachments else None
    )


async def setup(bot):
    await bot.add_cog(Audit(bot))
