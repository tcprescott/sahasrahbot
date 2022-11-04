import discord
from discord.commands import permissions, Option
from discord.ext import commands

from alttprbot.database import voicerole  # TODO switch to ORM


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

    # voicerole = discord.commands.SlashCommandGroup(
    #     "voicerole",
    #     "Commands for managing voice roles.",
    #     permissions=[permissions.CommandPermission(
    #         "owner", 2, True
    #     )
    #     ])

    # @voicerole.command(name='create')
    # async def vr_create(self, ctx, voice_channel: Option(discord.VoiceChannel, description="Voice channel to monitor."), role: Option(discord.Role, description="Role to assign to members in the voice channel.")):
    #     await voicerole.create_voice_role(ctx.guild.id, voice_channel.id, role.id)
    #     await ctx.respond(f"Created voice role mapping for {voice_channel.mention}", ephemeral=True)

    # @voicerole.command(name='delete')
    # async def vr_delete(self, ctx, role_id: int):
    #     await voicerole.delete_voice_role(ctx.guild.id, role_id)
    #     await ctx.respond(f"Deleted voice role mapping for {role_id}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VoiceRole(bot))
