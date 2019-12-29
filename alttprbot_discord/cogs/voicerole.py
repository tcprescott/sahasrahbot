import discord
from discord.ext import commands

from alttprbot.database import voicerole


class VoiceRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        vc_roles = await voicerole.get_voice_roles_by_guild(member.guild.id)

        if after.channel is not None and before.channel is not None:
            if after.channel.id == before.channel.id:
                return
        if after.channel is not None:
            for vc_role in vc_roles:
                if after.channel.id == vc_role['voice_channel_id']:
                    role = discord.utils.get(
                        member.guild.roles, id=vc_role['role_id'])
                    await member.add_roles(role, reason='Joined voice channel.')
        if before.channel is not None:
            for vc_role in vc_roles:
                if before.channel.id == vc_role['voice_channel_id']:
                    role = discord.utils.get(
                        member.guild.roles, id=vc_role['role_id'])
                    await member.remove_roles(role, reason='Left voice channel.')
        return

    @commands.group(aliases=['vr'])
    @commands.has_permissions(manage_roles=True)
    async def voicerole(self, ctx):
        pass

    @voicerole.command(name='create', aliases=['c'])
    async def vr_create(self, ctx, voice_channel: discord.VoiceChannel, role: discord.Role):
        await voicerole.create_voice_role(ctx.guild.id, voice_channel.id, role.id)

    @voicerole.command(name='delete', aliases=['d'])
    async def vr_delete(self, ctx, id: int):
        await voicerole.delete_voice_role(ctx.guild.id, id)


def setup(bot):
    bot.add_cog(VoiceRole(bot))
