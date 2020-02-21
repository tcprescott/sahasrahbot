import io
import zipfile

from discord.ext import commands

from alttprbot.database import config
from alttprbot.util import http


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
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

                elif attachment.filename.endswith(('.bat', '.exe', '.sh', '.py')) and await config.get(message.guild.id, 'DeleteExecutables') == "true":
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, please do not upload executable files.  If your message was deleted in error, please contact a moderator.')


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
