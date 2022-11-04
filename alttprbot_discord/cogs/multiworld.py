import logging
import re

# from discord.commands import Option
import discord
from alttprbot import models
from alttprbot.alttprgen.smz3multi import generate_multiworld
from discord.ext import commands
from discord import app_commands
from slugify import slugify

# TODO: make work with discord.py 2.0


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


# class MultiworldPresetDropdown(discord.ui.Select):
#     def __init__(self, randomizer, mwcreateview):
#         self.mwcreateview = mwcreateview

#         super().__init__(
#             placeholder="Choose a preset...",
#             min_values=1,
#             max_values=1,
#             options=PRESET_OPTIONS[randomizer],
#             row=1
#         )

#     async def callback(self, interaction: discord.Interaction):
#         self.mwcreateview.preset_name = self.values[0]


class MultiworldSignupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, error: Exception, item, interaction) -> None:
        raise error

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
    async def randomizer(self, select: discord.ui.Select, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)

        if not multiworld.owner_id == interaction.user.id:
            await interaction.response.send_message("You are not authorized to set the randomizer.", ephemeral=True)
            return

        multiworld.randomizer = select.values[0]
        multiworld.preset = None

        embed = interaction.message.embeds[0]
        embed = set_embed_field("Randomizer", multiworld.randomizer, embed)
        embed = set_embed_field("Preset", "Not yet chosen", embed)
        await multiworld.save()
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
    async def preset(self, select: discord.ui.Select, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)

        if not multiworld.owner_id == interaction.user.id:
            await interaction.response.send_message("You are not authorized set the preset.", ephemeral=True)
            return

        multiworld.preset = select.values[0]

        embed = interaction.message.embeds[0]
        embed = set_embed_field("Preset", multiworld.preset, embed)
        await multiworld.save(update_fields=['preset'])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.blurple, custom_id="sahabot:multiworld:join", row=3)
    async def join(self, button: discord.ui.Button, interaction: discord.Interaction):
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)
        entrant = await models.MultiworldEntrant.get_or_none(discord_user_id=interaction.user.id, multiworld=multiworld)
        if entrant:
            await interaction.response.pong()
            return
        await models.MultiworldEntrant.create(discord_user_id=interaction.user.id, multiworld=multiworld)

        await self.update_player_list(interaction.message)
        await interaction.response.pong()

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, custom_id="sahabot:multiworld:leave", row=3)
    async def leave(self, button: discord.ui.Button, interaction: discord.Interaction):
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)
        entrant = await models.MultiworldEntrant.get_or_none(discord_user_id=interaction.user.id, multiworld=multiworld)
        if entrant:
            await entrant.delete()

        await self.update_player_list(interaction.message)
        await interaction.response.pong()

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, custom_id="sahabot:multiworld:start", row=4)
    async def start(self, button: discord.ui.Button, interaction: discord.Interaction):
        message = interaction.message
        embed = message.embeds[0]
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)

        if not multiworld.owner_id == interaction.user.id:
            await interaction.response.send_message("You are not authorized to start this game.", ephemeral=True)
            return

        if not multiworld.randomizer or not multiworld.preset:
            await interaction.response.send_message("Please ensure you choose both a randomizer and preset before starting.", ephemeral=True)
            return

        embed = set_embed_field("Status", "⌚ Game closed for entry.  Rolling...", embed)
        await message.edit(embed=embed)

        await self.update_player_list(message)
        players = await self.get_player_members(message)

        if len(players) < 2:
            embed = set_embed_field("Status", "👍 Open for entry", embed)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.response.send_message("You must have at least two players to create a multiworld.", ephemeral=True)
            return

        await interaction.response.defer()

        player_names = [slugify(p.display_name, lowercase=False, max_length=19, separator=" ") for p in players]
        seed = await generate_multiworld(multiworld.preset, player_names, tournament=False, randomizer=multiworld.randomizer)

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

        multiworld.status = "CLOSED"
        await multiworld.save()

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="sahabot:multiworld:cancel", row=4)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        message = interaction.message
        embed = message.embeds[0]
        multiworld = await models.Multiworld.get(message_id=interaction.message.id)

        if not multiworld.owner_id == interaction.user.id:
            await interaction.response.send_message("You are not authorized to cancel this game.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed = set_embed_field("Status", "❌ Cancelled.", embed)
        multiworld.status = "CANCELLED"
        await multiworld.save()

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    async def update_player_list(self, message: discord.Message):
        embed = message.embeds[0]
        player_list_resp = await models.MultiworldEntrant.filter(multiworld__message_id=message.id)
        mentions = [f"<@{p.discord_user_id}>" for p in player_list_resp]

        if mentions:
            embed = set_embed_field("Players", '\n'.join(mentions), embed)
        else:
            embed = set_embed_field("Players", 'No players yet.', embed)

        await message.edit(embed=embed, view=self)

        return player_list_resp

    def allow_start(self, multiworld: models.Multiworld, entrants: models.MultiworldEntrant):
        return entrants > 2 and not multiworld.preset is None and not multiworld.randomizer is None

    async def get_player_members(self, message: discord.Message):
        guild = message.guild
        embed = message.embeds[0]
        player_list_resp = await models.MultiworldEntrant.filter(multiworld__message_id=message.id)
        entrant_discords = [await guild.fetch_member(p.discord_user_id) for p in player_list_resp]
        mentions = [p.mention for p in entrant_discords]

        if mentions:
            embed = set_embed_field("Players", '\n'.join(mentions), embed)
        else:
            embed = set_embed_field("Players", 'No players yet.', embed)

        return entrant_discords

class Multiworld(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False

    @ commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(MultiworldSignupView())
            self.persistent_views_added = True

    @commands.slash_command(name='multiworld')
    async def multiworld(self, interaction: discord.Interaction):
        """
        Creates a multiworld session
        """
        embed = discord.Embed(
            title=f'Multiworld Game',
            description=(
                'A new multiworld game has been initiated, click "Join" to join.  Click "Leave" to leave.\n'
                f'When everyone is ready the game creator, {ctx.author.mention}, can click "Start" to create a session.\n'
                f'The game creator can click "Cancel" to cancel this game.'
            ),
            color=discord.Color.dark_blue()
        )
        embed.add_field(name="Owner", value=ctx.author.mention, inline=False)
        embed.add_field(name="Status", value="👍 Open for entry", inline=False)
        embed.add_field(name="Randomizer", value="Not yet chosen", inline=False)
        embed.add_field(name="Preset", value="Not yet chosen", inline=False)
        embed.add_field(name="Players", value="No players yet.", inline=False)

        interaction_response: discord.Interaction = await ctx.interaction.response.send_message(embed=embed)
        original_message = await interaction_response.original_message()
        await models.Multiworld.create(message_id=original_message.id, owner_id=ctx.author.id, status="STARTED")
        await interaction_response.edit_original_message(embed=embed, view=MultiworldSignupView())


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


def get_owner(embed: discord.Embed, guild: discord.Guild) -> discord.Member:
    value = get_embed_field("Owner", embed)

    if value is None:
        return

    user_id = int(re.search('<@([0-9]*)>', value).groups()[0])
    return guild.get_member(user_id)


async def setup(bot):
    await bot.add_cog(Multiworld(bot))
