import io
import zipfile
import datetime

from urllib.parse import urlparse
from urlextract import URLExtract

import discord
from discord.ext import commands

from alttprbot.database import config
from alttprbot.util import http

urlextractor = URLExtract()

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return

        if message.author.joined_at > datetime.datetime.now()-datetime.timedelta(days=1) and await config.get(message.guild.id, 'ModerateNewMemberContent') == "true":
            for url in urlextractor.gen_urls(message.content):
                if urlparse(url).netloc in ['discord.gg']:
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, you must be on this server for longer than 24 hours before posting discord invite links.  Please contact a moderator if you want to post an invite link.')
            for attachment in message.attachments:
                if attachment.filename.endswith(('.bat', '.exe', '.sh', '.py')):
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, please do not upload executable files.  If your message was deleted in error, please contact a moderator.')

        # delete roms if server is configured to do so
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                if attachment.filename.endswith('.zip') and await config.get(message.guild.id, 'InspectZipArchives') == "true":
                    zippedfiles = await inspect_zip(attachment.url)
                    for zippedfile in zippedfiles:
                        if zippedfile.endswith(('.sfc', '.smc')) and await config.get(message.guild.id, 'DeleteRoms') == "true":
                            await message.delete()
                            await message.channel.send(f'{message.author.mention}, a ROM was detected in the zip archive posted.  If your message was deleted in error, please contact a moderator.')

                elif attachment.filename.endswith(('.sfc', '.smc')) and await config.get(message.guild.id, 'DeleteRoms') == "true":
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

def setup(bot):
    bot.add_cog(Moderation(bot))
