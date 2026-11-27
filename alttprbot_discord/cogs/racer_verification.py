import discord
from discord import app_commands
from discord.ext import commands

from alttprbot.services import racer_verification as verification
from alttprbot_discord.racer_verification import RacerVerificationView

__all__ = ['RacerVerification', 'RacerVerificationView', 'setup']


class RacerVerification(commands.GroupCog, name="racerverification"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(RacerVerificationView(self.bot))
            self.persistent_views_added = True

    @app_commands.command(description="Create a racer verification message.")
    @app_commands.describe(role="The role to assign to verified racers.")
    @app_commands.describe(racetime_categories="A comma-separated list of racetime categories to include in verification.")
    @app_commands.describe(use_alttpr_ladder="Set to true to include ALTTPR ladder in the verification requirements.")
    @app_commands.describe(minimum_races="Minimum number of races required to be verified.")
    @app_commands.describe(time_period_days="How long back to look to verify the racer.")
    @app_commands.describe(reverify_period_days="How often should the racer be required to reverify.  Leave blank to disable reverification.")
    @app_commands.describe(revoke_ineligible="Set to true to revoke the role from ineligible racers.")
    @app_commands.describe(audit_channel="Set to a channel to send a message to when a racer is revoked.")
    async def create_or_update(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        racetime_categories: str = None,
        use_alttpr_ladder: bool = False,
        minimum_races: int = 1,
        time_period_days: int = 365,
        reverify_period_days: int = None,
        revoke_ineligible: bool = False,
        audit_channel: discord.TextChannel = None,
    ):
        if not interaction.user.guild_permissions.administrator and not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        racer_verification = await verification.create_or_update(
            guild_id=interaction.guild.id,
            role_id=role.id,
            racetime_categories=racetime_categories,
            use_alttpr_ladder=use_alttpr_ladder,
            minimum_races=minimum_races,
            time_period_days=time_period_days,
            reverify_period_days=reverify_period_days,
            revoke_ineligible=revoke_ineligible,
            audit_channel_id=audit_channel.id if audit_channel else None,
        )

        content = verification.message_content(racer_verification)

        await interaction.response.send_message(
            content=content,
            view=RacerVerificationView(self.bot)
        )
        message = await interaction.original_response()
        await verification.attach_message(racer_verification, message.id, message.channel.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(RacerVerification(bot))
