import io
import logging
import zipfile
import datetime
from typing import List
import hashlib
import re

from urllib.parse import urlparse
from urlextract import URLExtract

import aiocache
import aiohttp
import discord
from discord.ext import commands

from alttprbot.util import http
from alttprbot import models

urlextractor = URLExtract()


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # don't moderate if a DM
        if message.guild is None:
            return

        # don't moderate if sent by a real bot
        if message.author.id == self.bot.user.id:
            return

        if message.author.bot:
            return

        # don't moderate if the user can amage guild, manage members, or is an administrator
        user_permissions = message.author.guild_permissions
        if user_permissions.manage_guild or user_permissions.moderate_members or user_permissions.administrator:
            return

        if hasattr(message.author, 'joined_at') and message.author.joined_at > discord.utils.utcnow()-datetime.timedelta(days=1):
            for url in urlextractor.gen_urls(message.content):
                link_domain = urlparse(url).netloc
                link_domain_hashed = hashlib.sha256(link_domain.encode('utf-8')).hexdigest()
                if link_domain in ['discord.gg']:
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, you must be on this server for longer than 24 hours before posting discord invite links.  Please contact a moderator if you want to post an invite link.')
            for attachment in message.attachments:
                if attachment.filename.endswith(('.bat', '.exe', '.sh', '.py')):
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, please do not upload executable files.  If your message was deleted in error, please contact a moderator.')

        try:
            phishing_hashes = await bad_domain_hashes()
            for url in urlextractor.gen_urls(message.content):
                link_domain = urlparse(url).netloc
                link_domain_hashed = hashlib.sha256(link_domain.encode('utf-8')).hexdigest()
                if link_domain_hashed in phishing_hashes:
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, your message seemed a bit... phishy.  🐟\n\nIf you\'re not a bot, please contact a moderator for assistance.')
                    await message.author.timeout(until=discord.utils.utcnow() + datetime.timedelta(minutes=30), reason="automated timeout for phishing")
        except Exception:
            logging.exception("Unable to scan message for phishing links.")

        # delete roms if server is configured to do so
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                if attachment.filename.endswith('.zip'):
                    zippedfiles = await inspect_zip(attachment.url)
                    for zippedfile in zippedfiles:
                        if zippedfile.endswith(('.sfc', '.smc')):
                            await message.delete()
                            await message.channel.send(f'{message.author.mention}, a ROM was detected in the zip archive posted.  If your message was deleted in error, please contact a moderator.')

                elif attachment.filename.endswith(('.sfc', '.smc')):
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, please do not post ROMs.  If your message was deleted in error, please contact a moderator.')

        # five_minutes = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)

        # if message.content and ck_url(message.content):
        #     previous_messages = await models.AuditMessages.filter(guild_id=message.guild.id, user_id=message.author.id, content=message.content, message_date__gte=five_minutes)

        #     if len(previous_messages) > 1:
        #         await message.author.timeout(until=discord.utils.utcnow() + datetime.timedelta(minutes=10), reason="automated timeout for duplicate messages")
        #         await message.channel.send(f"{message.author.mention}, your message was deleted because it was a duplicate of a recently sent message.  You have been timed out for 10 minutes.\n\nIf this was in error, please contact a moderator for assistance.")

        #         for audit_message in previous_messages:
        #             channel = self.bot.get_channel(audit_message.channel_id)
        #             try:
        #                 msg = await channel.fetch_message(audit_message.message_id)
        #             except discord.NotFound:
        #                 continue
        #             try:
        #                 await msg.delete()
        #             except discord.NotFound:
        #                 logging.warn(f"Unable to remove message id {message.id}")

        #         try:
        #             await message.delete()
        #         except discord.NotFound:
        #             logging.warn(f"Unable to remove message id {message.id}")


async def inspect_zip(url):
    binary = await http.request_generic(url, returntype='binary')
    with zipfile.ZipFile(io.BytesIO(binary), "r") as thezip:
        zippedfiles = thezip.namelist()

    return zippedfiles


@aiocache.cached(ttl=3600, cache=aiocache.SimpleMemoryCache)
async def bad_domain_hashes() -> List:
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method='get',
            url='https://cdn.discordapp.com/bad-domains/hashes.json',
            raise_for_status=True
        ) as resp:
            hashes: list = await resp.json()

    return hashes


def ck_url(string_to_check):
    re_equ = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    return bool(re.findall(re_equ, string_to_check))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
