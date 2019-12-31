import discord
from discord.ext import commands


class Audit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        print("message created")
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        print("message delete")

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        print("bulk message delete")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        print("message edit")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        print("removed reaction")

    @commands.Cog.listener()
    async def on_reaction_clear(self, message, reactions):
        print("cleared reactions")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        print("channel delete")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        print("channel create")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        print("channel update")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print("member join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        print("member remove")

    # role membership
    # display_name
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        print("member update")

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        print("user update")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        print("role create")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        print("role delete")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        print("role update")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        print("voice state change")

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        print("member ban")

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        print("member unban")

def setup(bot):
    bot.add_cog(Audit(bot))
