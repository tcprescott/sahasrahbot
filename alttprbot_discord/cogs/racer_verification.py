import discord
from discord import app_commands
from discord.ext import commands

from alttprbot.services import racer_verification as verification
from alttprbot_discord.audit import audited


class RacerVerificationView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Verify your status", custom_id="racerverify:verifystatus",
                       style=discord.ButtonStyle.primary)
    @audited('Verify your status button')
    async def verify_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        racer_verification = await verification.get_for_message(interaction.message.id, interaction.guild.id)

        if racer_verification is None:
            await interaction.followup.send(
                "This message is not a valid racer verification message.  This should not have happened.",
                ephemeral=True)
            return

        user = await verification.get_linked_user(interaction.user.id)
        if user is None:
            await interaction.followup.send(
                "Please visit https://sahasrahbotapi.synack.live/racetime/verification/initiate to link your RaceTime.gg ID!\n\nAfter that, click the button again!",
                ephemeral=True)
            return

        eligible, count = await verification.determine_eligibility(interaction.user.name, user, racer_verification)

        if eligible:
            await verification.record_verified(user, racer_verification, count)

            role = interaction.guild.get_role(racer_verification.role_id)
            await interaction.user.add_roles(role, reason="Racer Verification")
            await interaction.followup.send(f"Congratulations!  You have been verified!\n\nWe counted at least **{count}** races played over the last **{racer_verification.time_period_days}** days.", ephemeral=True)
        else:
            await interaction.followup.send(
                "Sorry, you do not meet the requirements for verification.  If you believe this is in error, please contact a server administrator for assistance.",
                ephemeral=True)


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

        rtgg_categories = racetime_categories.split(',') if racetime_categories is not None else []

        content = f"""
This message will be used to verify your status as a racer. You can click the button below to verify your status.
You must have a RaceTime.gg account linked to your Discord account to use this feature.
If you do not have a RaceTime.gg account, please visit <https://racetime.gg> to create one.

If you have any questions, please contact a server administrator.

**Requirements:**
- Must have a RaceTime.gg account linked to your Discord account via SahasrahBot.  You will be supplied a link to do so if this is not already done.
- Have at least {minimum_races} {'race' if minimum_races == 1 else 'races'} played in the last {time_period_days} {'day' if time_period_days == 1 else 'days'} on RaceTime.gg in the following categories: {', '.join(rtgg_categories)}{' or ALTTPR Ladder races ' if use_alttpr_ladder else ''}
- Must be a member of this Discord server
"""


        await interaction.response.send_message(
            content=content,
            view=RacerVerificationView(self.bot)
        )
        message = await interaction.original_response()
        await verification.attach_message(racer_verification, message.id, message.channel.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(RacerVerification(bot))
