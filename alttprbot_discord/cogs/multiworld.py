from discord.ext import commands
from discord.commands import Option
import discord

from alttprbot import models
from alttprbot.alttprgen.smz3multi import generate_multiworld

PRESET_OPTIONS = {
    'sm': [
        discord.SelectOption(label="casual_full"),
        discord.SelectOption(label="casual_split"),
        discord.SelectOption(label="tournament_full"),
        discord.SelectOption(label="tournament_split"),
    ],
    'smz3': [
        discord.SelectOption(label="casual"),
        discord.SelectOption(label="casualkeys"),
        discord.SelectOption(label="hard"),
        discord.SelectOption(label="hardkeys"),
        discord.SelectOption(label="normal"),
        discord.SelectOption(label="normalkeys"),
    ]
}


class MultiworldPresetDropdown(discord.ui.Select):
    def __init__(self, randomizer, mwcreateview):
        self.mwcreateview = mwcreateview

        super().__init__(
            placeholder="Choose a preset...",
            min_values=1,
            max_values=1,
            options=PRESET_OPTIONS[randomizer],
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        self.mwcreateview.preset_name = self.values[0]


class MultiworldSignupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Join/Leave", style=discord.ButtonStyle.blurple, custom_id="sahabot:multiworld:create")
    async def join_leave(self, button: discord.ui.Button, interaction: discord.Interaction):
        entrant = await models.MultiworldEntrant.get_or_none(discord_user_id=interaction.user.id, multiworld_id=interaction.message.id)
        if entrant is None:
            await models.MultiworldEntrant.create(discord_user_id=interaction.user.id, multiworld_id=interaction.message.id)
        else:
            await entrant.delete()

        await self.update_player_list(interaction.message)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, custom_id="sahabot:multiworld:start")
    async def start(self, button: discord.ui.Button, interaction: discord.Interaction):
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)

        if not multiworld.owner_id == interaction.user.id:
            await interaction.response.send_message("You are not authorized to start this game.", ephemeral=True)
            return

        message = interaction.message
        embed = message.embeds[0]
        embed.set_field_at(0, name="Status", value="⌚ Game closed for entry.  Rolling...")
        await message.edit(embed=embed)

        await self.update_player_list(message)
        players = await self.get_player_members(message)

        if len(players) < 2:
            await interaction.response.send_message("You must have at least two players to create a multiworld.", ephemeral=True)
            embed.set_field_at(0, name="Status", value="👍 Open for entry")
            await message.edit(embed=embed)
            return

        seed = await generate_multiworld(multiworld.preset, [p.name for p in players], tournament=False, randomizer=multiworld.randomizer)

        dm_embed = discord.Embed(
            title=f"{multiworld.randomizer.upper()} Multiworld Game"
        )
        dm_embed.add_field(name="Players", value='\n'.join([p.name for p in players]), inline=False)
        dm_embed.add_field(name="Game Room", value=seed.url, inline=False)

        for player in players:
            try:
                await player.send(embed=dm_embed)
            except discord.HTTPException:
                await message.reply(f"Unable to send DM to {player.mention}!")

        embed.set_field_at(0, name="Status", value="✅ Game started!  Check your DMs.")

        multiworld.status = "CLOSED"
        await multiworld.save()

        self.clear_items()
        await message.edit(embed=embed, view=self)
        await interaction.response.send_message("Game started, check your DMs!")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="sahabot:multiworld:cancel")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)

        if not multiworld.owner_id == interaction.user.id:
            await interaction.response.send_message("You are not authorized to cancel this game.", ephermal=True)
            return

        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="Status", value="❌ Cancelled.")
        await interaction.message.edit(embed=embed)
        multiworld.status = "CANCELLED"
        await multiworld.save()

        self.clear_items()
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Game started, check your DMs!")

    async def update_player_list(self, message: discord.Message):
        embed = message.embeds[0]
        player_list_resp = await models.MultiworldEntrant.filter(multiworld__message_id=message.id)
        mentions = [f"<@{p.discord_user_id}>" for p in player_list_resp]

        if mentions:
            embed.set_field_at(2, name="Players", value='\n'.join(mentions))
        else:
            embed.set_field_at(2, name="Players", value='No players yet.')

        await message.edit(embed=embed)

    async def get_player_members(self, message: discord.Message):
        guild = message.guild
        embed = message.embeds[0]
        player_list_resp = await models.MultiworldEntrant.filter(multiworld__message_id=message.id)
        entrant_discords = [await guild.fetch_member(p.discord_user_id) for p in player_list_resp]
        mentions = [p.mention for p in entrant_discords]

        if mentions:
            embed.set_field_at(2, name="Players", value='\n'.join(mentions))
        else:
            embed.set_field_at(2, name="Players", value='No players yet.')

        return entrant_discords


class MultiworldCreateView(discord.ui.View):
    def __init__(self, randomizer):
        super().__init__(timeout=300)
        self.randomizer = randomizer
        self.preset_name = None
        self.add_item(MultiworldPresetDropdown(self.randomizer, self))

    @discord.ui.button(label="Create", style=discord.ButtonStyle.green, row=2)
    async def create(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f'{self.randomizer.upper()} Multiworld Game',
            description=(
                'A new multiworld game has been initiated, click "Join" to join.\n'
                'When everyone is ready, the game creator can click "Start" to create a session.\n'
                'The game creator can click "Cancel" to cancel this game.'
            ),
            color=discord.Color.dark_blue()
        )
        embed.add_field(name="Status", value="👍 Open for entry", inline=False)
        embed.add_field(name="Preset", value=f"[{self.preset_name.lower()}](https://github.com/tcprescott/sahasrahbot/blob/master/presets/{self.randomizer.lower()}/{self.preset_name.lower()}.yaml)", inline=False)
        embed.add_field(name="Players", value="No players yet.", inline=False)

        message = await interaction.channel.send(embed=embed)
        await models.Multiworld.create(message_id=message.id, owner_id=interaction.user.id, randomizer=self.randomizer, preset=self.preset_name, status="STARTED")
        await message.edit(view=MultiworldSignupView())


class Multiworld(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(MultiworldSignupView())
            self.persistent_views_added = True

    @commands.slash_command(name='multiworld')
    async def multiworld(self, ctx, randomizer: Option(str, description="Choose a randomizer", choices=['sm', 'smz3'])):
        """
        Creates a multiworld session
        """
        view = MultiworldCreateView(randomizer=randomizer)
        await ctx.respond("Choose a preset and click Create to start signups for this multiworld session.\n\nIf you did this in error, just click \"Dismiss message\".", view=view, ephemeral=True)


def setup(bot):
    bot.add_cog(Multiworld(bot))
