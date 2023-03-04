import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from config import Config as c


class DoorsMultiworld(commands.GroupCog, name="doorsmw", description="ALTTP Door Randomizer multiworld."):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(description="Create a new multiworld host.")
    async def host(self, interaction: discord.Interaction, multidata: discord.Attachment, race: bool = False):
        data = {
            'multidata_url': multidata.url,
            'admin': interaction.user.id,
            'racemode': race,
            'meta': {
                'channel': interaction.channel.name if interaction.channel.guild else None,
                'guild': interaction.guild.name if interaction.guild else None,
                'multidata_url': multidata.url,
                'name': f'{interaction.user.name}#{interaction.user.discriminator}'
            }
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:5002/game', json=data) as resp:
                    multiworld = await resp.json()
        except aiohttp.ClientResponseError as err:
            raise SahasrahBotException(
                'Unable to generate host using the provided multidata.  Ensure you\'re using the latest version of the mutiworld (<https://github.com/Bonta0/ALttPEntranceRandomizer/tree/multiworld_31>)!') from err

        if not multiworld.get('success', True):
            raise SahasrahBotException(
                f"Unable to generate host using the provided multidata.  {multiworld.get('description', '')}")

        await interaction.response.send_message(embed=make_embed(multiworld))
        await interaction.response.send_message("New multiworld", ephemeral=True)

    @app_commands.command(description="Resume a multiworld that was previously closed.")
    async def resume(self, interaction: discord.Interaction, token: str, port: int):
        data = {
            'token': token,
            'port': port,
            'admin': interaction.user.id,
            'meta': {
                'channel': interaction.channel.name if interaction.channel.guild else None,
                'guild': interaction.guild.name if interaction.guild else None,
                'name': f'{interaction.user.name}#{interaction.user.discriminator}'
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:5002/game', json=data) as resp:
                multiworld = await resp.json()
        await interaction.response.send_message(embed=make_embed(multiworld))

    @app_commands.command(description="Send a message to the multiworld server.")
    async def msg(self, interaction: discord.Interaction, token: str, msg: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://localhost:5002/game/{token}') as multiworld_resp:
                multiworld = await multiworld_resp.json()

        if not multiworld.get('success', True):
            raise SahasrahBotException("That game does not exist.")

        if not (multiworld['admin'] == interaction.user.id):
            raise SahasrahBotException('You must be the creator of the game to send messages to it.')

        data = {
            'msg': msg
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(f'http://localhost:5002/game/{token}/msg', json=data) as msg_response:
                response = await msg_response.json()

        if response.get('success', True) is False:
            raise SahasrahBotException(response.get(
                'error', 'Unknown error occured while processing message.'))

        if 'resp' in response and response['resp'] is not None:
            await interaction.response.send_message(response['resp'])
        else:
            await interaction.response.send_message("Message sent to multiworld server.  No response received (this may be normal).")


def make_embed(multiworld):
    embed = discord.Embed(
        title='Multiworld Game',
        description='Here are the details of your multiworld game.',
        color=discord.Color.green()
    )
    embed.add_field(name="Game Token", value=multiworld['token'], inline=False)
    embed.add_field(
        name="Host", value=f"{c.MultiworldHostBase}:{multiworld['port']}", inline=False)
    for idx, team in enumerate(multiworld.get('players', []), start=1):
        if len(team) < 50:
            embed.add_field(name=f"Team #{idx}", value='\n'.join(team))

    return embed


async def setup(bot):
    await bot.add_cog(DoorsMultiworld(bot))
