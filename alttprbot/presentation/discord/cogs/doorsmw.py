import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import config
from alttprbot.exceptions import SahasrahBotException


def create_deprecation_embed() -> discord.Embed:
    """Create a standardized deprecation message embed."""
    return discord.Embed(
        title="⚠️ Feature Retired",
        description=(
            "Discord multiworld hosting has been retired and is no longer available.\n\n"
            "**Timeline:** This feature will be fully removed in the next bot release.\n\n"
            "**Alternative:** No in-bot replacement is planned. "
            "Please use other multiworld hosting solutions outside of Discord.\n\n"
            "Other bot features like seed generation (`/generate`), tournaments, and community commands remain fully supported."
        ),
        color=discord.Color.orange()
    )


class DoorsMultiworld(commands.GroupCog, name="doorsmw", description="[DEPRECATED] Multiworld hosting has been retired."):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def host(self, interaction: discord.Interaction, multidata: discord.Attachment, race: bool = False):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def resume(self, interaction: discord.Interaction, token: str):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def kick(self, interaction: discord.Interaction, token: str, player: str):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def close(self, interaction: discord.Interaction, token: str):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def forfeit(self, interaction: discord.Interaction, token: str, player: str):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def send(self, interaction: discord.Interaction, token: str, player: str, item: str):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def password(self, interaction: discord.Interaction, token: str, password: str):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)

    @forfeit.autocomplete("player")
    @send.autocomplete("player")
    async def autocomplete_player(self, interaction: discord.Interaction, current: str):
        token = interaction.namespace.token
        params = {
            'player': current,
            'token': token
        }
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:5002/autocomplete/players', params=params) as resp:
                result = await resp.json()

        return [app_commands.Choice(name=player, value=player) for player in result]

    @send.autocomplete("item")
    async def autocomplete_item(self, interaction: discord.Interaction, current: str):
        params = {
            'item': current
        }
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:5002/autocomplete/items', params=params) as resp:
                result = await resp.json()

        return [app_commands.Choice(name=item, value=item) for item in result]

    @kick.autocomplete("player")
    async def autocomplete_kick(self, interaction: discord.Interaction, current: str):
        token = interaction.namespace.token
        params = {
            'client': current,
            'token': token
        }
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:5002/autocomplete/clients', params=params) as resp:
                result = await resp.json()

        return [app_commands.Choice(name=client, value=client) for client in result]

    @app_commands.command(description="[DEPRECATED] Multiworld hosting has been retired.")
    async def msg(self, interaction: discord.Interaction, token: str, msg: str):
        await interaction.response.send_message(embed=create_deprecation_embed(), ephemeral=True)


async def send_command(token, interaction: discord.Interaction, **data):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://localhost:5002/game/{token}') as multiworld_resp:
            multiworld = await multiworld_resp.json()

    if not multiworld.get('success', True):
        raise SahasrahBotException("That game does not exist.")

    if not (multiworld['admin'] == interaction.user.id):
        raise SahasrahBotException('You must be the creator of the game to send items to players.')

    async with aiohttp.ClientSession() as session:
        async with session.put(f'http://localhost:5002/game/{token}/cmd', json=data) as send_response:
            response = await send_response.json()

    if response.get('success', True) is False:
        return response.get('error', response.get('description', 'Unknown error occured while processing command.'))

    return response.get('resp', 'Command sent to multiworld server.  No response received (this may be normal).')


def make_embed(multiworld):
    embed = discord.Embed(
        title='Multiworld Game',
        description='Here are the details of your multiworld game.',
        color=discord.Color.green()
    )
    embed.add_field(name="Game Token", value=multiworld['token'], inline=False)
    embed.add_field(
        name="Host", value=f"{config.MULTIWORLDHOSTBASE}:{multiworld['port']}", inline=False)
    for idx, team in enumerate(multiworld.get('players', []), start=1):
        if len(team) < 50:
            embed.add_field(name=f"Team #{idx}", value='\n'.join(team))

    return embed


async def setup(bot):
    await bot.add_cog(DoorsMultiworld(bot))
