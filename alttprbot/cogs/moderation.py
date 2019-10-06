import discord
from discord.ext import commands

from ..database import config

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        
        # delete roms if server is configured to do so
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                if attachment.filename.endswith(('.sfc','.smc')):
                    if await should_delete_message(message.guild.id):
                        await message.delete()
                        await message.channel.send(f'{message.author.mention} Please do not post ROMs.  If your message was deleted in error, please contact a moderator.')

async def should_delete_message(guild_id):
    deleteroms = await config.get_parameter(guild_id, 'DeleteRoms')
    if deleteroms and deleteroms['value'] == 'true':
        return True
    else:
        return False

def setup(bot):
    bot.add_cog(Moderation(bot))