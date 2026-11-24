import logging

import discord
from discord import app_commands
from discord.ext import commands
from slugify import slugify

from alttprbot.services import multiworld as multiworld_service
from alttprbot.services.multiworld import MultiworldNotAuthorized, MultiworldNotReady

NOT_YET_CHOSEN = "Not yet chosen"

# TODO: make these dynamic based on current presets
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
        discord.SelectOption(label="dungeons"),
        discord.SelectOption(label="fastkeysrandom"),
        discord.SelectOption(label="fastrandom"),
        discord.SelectOption(label="hard"),
        discord.SelectOption(label="hard553"),
        discord.SelectOption(label="harddungeons"),
        discord.SelectOption(label="hardfastkeysrandom"),
        discord.SelectOption(label="hardfastrandom"),
        discord.SelectOption(label="hardkeys"),
        discord.SelectOption(label="hardquick"),
        discord.SelectOption(label="hardrandom"),
        discord.SelectOption(label="normal"),
        discord.SelectOption(label="normal553"),
        discord.SelectOption(label="normalkeys"),
        discord.SelectOption(label="quick"),
        discord.SelectOption(label="random"),
    ]
}


class MultiworldSignupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Choose a randomizer",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="smz3", description="SM + ALTTP Combo Randomizer"),
            discord.SelectOption(label="sm", description="Super Metroid Randomizer")
        ],
        custom_id="sahabot:multiworld:randomizer",
        row=1
    )
    async def randomizer(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            multiworld = await multiworld_service.set_randomizer(interaction.message.id, interaction.user.id,
                                                                 select.values[0])
        except MultiworldNotAuthorized:
            await interaction.response.send_message("You are not authorized to set the randomizer.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed = set_embed_field("Randomizer", multiworld.randomizer, embed)
        embed = set_embed_field("Preset", NOT_YET_CHOSEN, embed)
        preset_select: discord.ui.Select = discord.utils.get(self.children, custom_id='sahabot:multiworld:preset')
        preset_select.disabled = False
        preset_select.options = PRESET_OPTIONS[multiworld.randomizer]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="Choose a preset",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="none", description="Choose a randomizer first!")
        ],
        custom_id="sahabot:multiworld:preset",
        row=2,
        disabled=True
    )
    async def preset(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            multiworld = await multiworld_service.set_preset(interaction.message.id, interaction.user.id,
                                                             select.values[0])
        except MultiworldNotAuthorized:
            await interaction.response.send_message("You are not authorized set the preset.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed = set_embed_field("Preset", multiworld.preset, embed)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.blurple, custom_id="sahabot:multiworld:join", row=3)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await multiworld_service.join(interaction.message.id, interaction.user.id):
            await interaction.response.send_message("You are already signed up for this multiworld.", ephemeral=True)
            return

        await self.update_player_list(interaction.message)
        await interaction.response.send_message("You have been added to the multiworld.", ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, custom_id="sahabot:multiworld:leave", row=3)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await multiworld_service.leave(interaction.message.id, interaction.user.id)

        await self.update_player_list(interaction.message)
        await interaction.response.send_message("You have been removed from the multiworld.", ephemeral=True)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, custom_id="sahabot:multiworld:start", row=4)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        message = interaction.message
        embed = message.embeds[0]
        try:
            multiworld = await multiworld_service.check_can_start(interaction.message.id, interaction.user.id)
        except MultiworldNotAuthorized:
            await interaction.response.send_message("You are not authorized to start this game.", ephemeral=True)
            return
        except MultiworldNotReady:
            await interaction.response.send_message(
                "Please ensure you choose both a randomizer and preset before starting.", ephemeral=True)
            return

        embed = set_embed_field("Status", "⌚ Game closed for entry.  Rolling...", embed)
        await message.edit(embed=embed)

        await self.update_player_list(message)
        players = await self.get_player_members(message)

        if not multiworld_service.has_enough_players(len(players)):
            embed = set_embed_field("Status", "👍 Open for entry", embed)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.response.send_message("You must have at least two players to create a multiworld.",
                                                    ephemeral=True)
            return

        await interaction.response.defer()

        player_names = [slugify(p.display_name, lowercase=False, max_length=19, separator=" ") for p in players]
        seed = await multiworld_service.start(multiworld, player_names)

        dm_embed = discord.Embed(
            title=f"{multiworld.randomizer.upper()} Multiworld Game"
        )
        dm_embed.add_field(name="Players", value='\n'.join([p.name for p in players]), inline=False)
        dm_embed.add_field(name="Game Room", value=seed.url, inline=False)

        for player in players:
            try:
                await player.send(embed=dm_embed)
            except Exception:
                logging.exception(f"Unable to send DM to {player.mention}!")

            embed = set_embed_field("Status", "✅ Game started!  Check your DMs.", embed)

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="sahabot:multiworld:cancel", row=4)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        message = interaction.message
        try:
            await multiworld_service.cancel(message.id, interaction.user.id)
        except MultiworldNotAuthorized:
            await interaction.response.send_message("You are not authorized to cancel this game.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed = set_embed_field("Status", "❌ Cancelled.", embed)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    async def update_player_list(self, message: discord.Message):
        embed = message.embeds[0]
        player_ids = await multiworld_service.entrant_ids(message.id)
        mentions = [f"<@{user_id}>" for user_id in player_ids]

        if mentions:
            embed = set_embed_field("Players", '\n'.join(mentions), embed)
        else:
            embed = set_embed_field("Players", 'No players yet.', embed)

        await message.edit(embed=embed, view=self)

        return player_ids

    async def get_player_members(self, message: discord.Message):
        guild = message.guild
        embed = message.embeds[0]
        player_ids = await multiworld_service.entrant_ids(message.id)
        entrant_discords = [await guild.fetch_member(user_id) for user_id in player_ids]
        mentions = [p.mention for p in entrant_discords]

        if mentions:
            embed = set_embed_field("Players", '\n'.join(mentions), embed)
        else:
            embed = set_embed_field("Players", 'No players yet.', embed)

        return entrant_discords


class SMMulti(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(MultiworldSignupView())
            self.persistent_views_added = True

    @app_commands.command(description="Creates a multiworld session for SM and SMZ3.")
    async def smmulti(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title='Multiworld Game',
            description=(
                'A new multiworld game has been initiated, click "Join" to join.  Click "Leave" to leave.\n'
                f'When everyone is ready the game creator, {interaction.user.mention}, can click "Start" to create a session.\n'
                f'The game creator can click "Cancel" to cancel this game.'
            ),
            color=discord.Color.dark_blue()
        )
        embed.add_field(name="Owner", value=interaction.user.mention, inline=False)
        embed.add_field(name="Status", value="👍 Open for entry", inline=False)
        embed.add_field(name="Randomizer", value=NOT_YET_CHOSEN, inline=False)
        embed.add_field(name="Preset", value=NOT_YET_CHOSEN, inline=False)
        embed.add_field(name="Players", value="No players yet.", inline=False)

        await interaction.response.send_message(embed=embed)
        original_message = await interaction.original_response()
        await multiworld_service.create(original_message.id, interaction.user.id)
        await original_message.edit(embed=embed, view=MultiworldSignupView())


def set_embed_field(name: str, value: str, embed: discord.Embed) -> discord.Embed:
    for idx, field in enumerate(embed.fields):
        if field.name == name:
            embed.set_field_at(idx, name=name, value=value, inline=field.inline)
    return embed


def get_embed_field(name: str, embed: discord.Embed) -> str:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None


async def setup(bot):
    await bot.add_cog(SMMulti(bot))
