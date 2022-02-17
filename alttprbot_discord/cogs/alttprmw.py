import discord
from discord.commands import Option
from aiohttp import ClientResponseError
from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.util import http
from config import Config as c


class AlttprMW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    alttprmw = discord.commands.SlashCommandGroup("alttprmw", "Bonta Multiworld", "Bonta Multiworld commands")

    @alttprmw.command()
    async def host(
        self,
        ctx: discord.ApplicationContext,
        multidata: Option(discord.Attachment, "Multiworld data", required=True),
        use_server_options: Option(bool, "Use server options?") = False,
    ):
        """
        Uploads a multiworld file to the Bonta Multiworld server.
        """
        data = {
            'multidata_url': multidata.url,
            'admin': ctx.author.id,
            'use_server_options': use_server_options,
            'meta': {
                'channel': None if isinstance(ctx.channel, discord.DMChannel) else ctx.channel.name,
                'guild': ctx.guild.name if ctx.guild else None,
                'multidata_url': multidata.url,
                'name': f'{ctx.author.name}#{ctx.author.discriminator}'
            }
        }
        try:
            multiworld = await http.request_json_post(url='http://localhost:5000/game', data=data, returntype='json')
        except ClientResponseError as err:
            raise SahasrahBotException(
                'Unable to generate host using the provided multidata.  Ensure you\'re using the latest version of the mutiworld (<https://github.com/Bonta0/ALttPEntranceRandomizer/tree/multiworld_31>)!') from err

        if not multiworld.get('success', True):
            raise SahasrahBotException(
                f"Unable to generate host using the provided multidata.  {multiworld.get('description', '')}")

        await ctx.respond(embed=make_embed(multiworld))

    @alttprmw.command()
    async def msg(self, ctx, token: Option(str, "Game token to send the message."), msg: Option(str, "Message to send to the game.")):
        """
        Send a command to the multiworld server.
        """
        result = await http.request_generic(url=f'http://localhost:5000/game/{token}', method='get', returntype='json')

        if not result.get('success', True):
            raise SahasrahBotException("That game does not exist.")

        if not result['admin']:
            raise SahasrahBotException(
                'You must be the creator of the game to send messages to it.')

        data = {
            'msg': msg
        }
        response = await http.request_json_put(url=f'http://localhost:5000/game/{token}/msg', data=data, returntype='json')

        if response.get('success', True) is False:
            raise SahasrahBotException(response.get(
                'error', 'Unknown error occured while processing message.'))

        if 'resp' in response and response['resp'] is not None:
            await ctx.respond(response['resp'])

    @alttprmw.command()
    async def resume(self, ctx, token: Option(str, "Game token"), port: Option(int, "Port #"), use_server_options: Option(bool, "Use server options?") = False):
        """
        Resume an existing multiworld that was previously closed.
        """
        data = {
            'token': token,
            'port': port,
            'admin': ctx.author.id,
            'use_server_options': use_server_options,
            'meta': {
                'channel': None if isinstance(ctx.channel, discord.DMChannel) else ctx.channel.name,
                'guild': ctx.guild.name if ctx.guild else None,
                'name': f'{ctx.author.name}#{ctx.author.discriminator}'
            }
        }
        multiworld = await http.request_json_post(url='http://localhost:5000/game', data=data, returntype='json')

        await ctx.respond(embed=make_embed(multiworld))


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


def setup(bot):
    bot.add_cog(AlttprMW(bot))
