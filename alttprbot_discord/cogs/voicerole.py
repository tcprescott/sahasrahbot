import discord
from discord.ext import commands

from alttprbot.services import voice_roles


def _roles_for_channel(guild, vc_roles, channel_id):
    """The guild roles mapped to this voice channel (skipping roles that no longer exist)."""
    for vc_role in vc_roles:
        if vc_role.voice_channel_id == channel_id:
            role = discord.utils.get(guild.roles, id=vc_role.role_id)
            if role is not None:
                yield role


class VoiceRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel is not None and before.channel is not None and after.channel.id == before.channel.id:
            return

        vc_roles = await voice_roles.for_guild(member.guild.id)
        if after.channel is not None:
            for role in _roles_for_channel(member.guild, vc_roles, after.channel.id):
                await member.add_roles(role, reason='Joined voice channel.')
        if before.channel is not None:
            for role in _roles_for_channel(member.guild, vc_roles, before.channel.id):
                await member.remove_roles(role, reason='Left voice channel.')


async def setup(bot):
    await bot.add_cog(VoiceRole(bot))
