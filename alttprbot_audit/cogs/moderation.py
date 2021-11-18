import io
import zipfile
import datetime
from typing import List
import hashlib

from urllib.parse import urlparse
from urlextract import URLExtract

import aiocache
import aiohttp
import discord
from discord.ext import commands

from alttprbot.database import config  # TODO switch to ORM
from alttprbot.util import http

urlextractor = URLExtract()


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return

        if hasattr(message.author, 'joined_at') and message.author.joined_at > discord.utils.utcnow()-datetime.timedelta(days=1) and await message.guild.config_get('ModerateNewMemberContent') == "true" and not message.author.id == self.bot.user.id:
            phishing_hashes = await bad_domain_hashes()
            for url in urlextractor.gen_urls(message.content):
                link_domain = urlparse(url).netloc
                link_domain_hashed = hashlib.sha256(link_domain.encode('utf-8')).hexdigest()
                if link_domain in ['discord.gg']:
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, you must be on this server for longer than 24 hours before posting discord invite links.  Please contact a moderator if you want to post an invite link.')
                if link_domain_hashed in phishing_hashes:
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, your message seemed a bit... phishy.  🐟\n\nIf you\'re not a bot, please contact a moderator for assistance.')
            for attachment in message.attachments:
                if attachment.filename.endswith(('.bat', '.exe', '.sh', '.py')):
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, please do not upload executable files.  If your message was deleted in error, please contact a moderator.')

        # delete roms if server is configured to do so
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                if attachment.filename.endswith('.zip') and await message.guild.config_get('InspectZipArchives') == "true":
                    zippedfiles = await inspect_zip(attachment.url)
                    for zippedfile in zippedfiles:
                        if zippedfile.endswith(('.sfc', '.smc')) and await message.guild.config_get('DeleteRoms') == "true":
                            await message.delete()
                            await message.channel.send(f'{message.author.mention}, a ROM was detected in the zip archive posted.  If your message was deleted in error, please contact a moderator.')

                elif attachment.filename.endswith(('.sfc', '.smc')) and await message.guild.config_get('DeleteRoms') == "true":
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, please do not post ROMs.  If your message was deleted in error, please contact a moderator.')


async def inspect_zip(url):
    binary = await http.request_generic(url, returntype='binary')
    with zipfile.ZipFile(io.BytesIO(binary), "r") as thezip:
        zippedfiles = thezip.namelist()

    return zippedfiles


async def should_delete_message(guild_id):
    deleteroms = await config.get_parameter(guild_id, 'DeleteRoms')
    if deleteroms and deleteroms['value'] == 'true':
        return True
    else:
        return False


@aiocache.cached(ttl=28800, cache=aiocache.SimpleMemoryCache)
async def bad_domain_hashes() -> List:
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method='get',
            url='https://cdn.discordapp.com/bad-domains/hashes.json',
            raise_for_status=True
        ) as resp:
            hashes: list = await resp.json()

    return hashes


def setup(bot):
    bot.add_cog(Moderation(bot))
