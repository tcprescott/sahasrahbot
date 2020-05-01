import io
import lzma
import zipfile
import yaml

import discord
from aiohttp import ClientResponseError
from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.util import http
from config import Config as c


class BontaMultiworld(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help=('Host a multiworld using an attached multidata file from Bonta\'s multiworld implementation.\n'
              'The multidata file that is attached must be from the multiworld_31 branch or another compatible implementation, such as Berserker\'s MultiWorld Utilities.\n\n'
              'The use_server_options option, when enabled, will use the server_options embedded in the multidata file, if it exists.\n\n'
              'Returns a "token" that can be used with the $mwmsg command to send commands to the server console.\n\n'
              'Warning: Games are automatically closed after 24 hours.  If you require more time than that, you may re-open the game using $mwresume'
        ),
        brief='Host a multiworld using Bonta\'s multiworld implementation.'
    )
    async def mwhost(self, ctx, use_server_options: bool = False):
        if not ctx.message.attachments:
            raise SahasrahBotException('Must attach a multidata file.')

        data = {
            'multidata_url': ctx.message.attachments[0].url,
            'admin': ctx.author.id,
            'use_server_options': use_server_options,
            'meta': {
                'channel': None if isinstance(ctx.channel, discord.DMChannel) else ctx.channel.name,
                'guild': ctx.guild.name if ctx.guild else None,
                'multidata_url': ctx.message.attachments[0].url,
                'name': f'{ctx.author.name}#{ctx.author.discriminator}'
            }
        }
        try:
            multiworld = await http.request_json_post(url='http://localhost:5000/game', data=data, returntype='json')
        except ClientResponseError as err:
            raise SahasrahBotException('Unable to generate host using the provided multidata.  Ensure you\'re using the latest version of the mutiworld (<https://github.com/Bonta0/ALttPEntranceRandomizer/tree/multiworld_31>)!') from err

        if not multiworld.get('success', True):
            raise SahasrahBotException(f"Unable to generate host using the provided multidata.  {multiworld.get('description', '')}")

        await ctx.send(embed=make_embed(multiworld))

    @commands.command(
        help=(
            'Sends a command to the multiworld server.\n'
            'The msg should be wrapped in quotes.  For example: $mwmsg abc123 "/kick Synack"\n'
            'Only the creator of the game, or the owner of this bot, may send commands.'
        ),
        brief='Send a command to the multiworld server.'
    )
    async def mwmsg(self, ctx, token, msg):
        result = await http.request_generic(url=f'http://localhost:5000/game/{token}', method='get', returntype='json')

        if not result['admin'] == ctx.author.id and not (token == 'v40la3' and msg.startswith('/kick ')):
            raise SahasrahBotException('You must be the creator of the game to send messages to it.')

        data = {
            'msg': msg
        }
        response = await http.request_json_put(url=f'http://localhost:5000/game/{token}/msg', data=data, returntype='json')

        if response.get('success', True) is False:
            raise SahasrahBotException(response.get('error', 'Unknown error occured while processing message.'))

        if 'resp' in response and response['resp'] is not None:
            await ctx.send(response['resp'])

    @commands.command(
        help=(
            'Resume an existing multiworld that was previously closed.\n'
            'Specify the existing token, and port number.\n\n'
            'Multidata and multisave file are removed from the server after 7 days.'
        ),
        brief='Resume a multiworld that was previously closed.'
    )
    async def mwresume(self, ctx, token, port, use_server_options: bool=False):
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

        await ctx.send(embed=make_embed(multiworld))

    @commands.command(
        help=(
            "Attach a zip file that contains the bmbp patches you wish to update.\n"
            "Command will return a zip file with corrected patch files.\n\n"
            "The hoststring should be in \"hostname:port\" format."
        ),
        brief="Update hostname in a zip file of bmbp patches."
    )
    async def mwfixpatch(self, ctx, hoststring):
        if not ctx.message.attachments:
            raise SahasrahBotException('Must attach a zip file.')

        binary = await ctx.message.attachments[0].read()

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(io.BytesIO(binary), "r") as oldzip:
            with zipfile.ZipFile(zip_buffer, "w") as newzip:
                bmbp_files = [f for f in oldzip.namelist() if f.endswith('.bmbp')]
                for bmbp_file in bmbp_files:
                    with oldzip.open(bmbp_file, 'r') as bmbp:
                        content = yaml.load(lzma.decompress(bmbp.read()), Loader=yaml.SafeLoader)
                        try:
                            content['meta']['server'] = hoststring
                        except KeyError:
                            pass
                    
                    new_file = yaml.dump(content).encode(encoding="utf-8-sig")
                    newzip.writestr(bmbp_file, lzma.compress(new_file))

        zip_to_send = zip_buffer.getvalue()
        await ctx.send(file=discord.File(fp=io.BytesIO(zip_to_send), filename=f'Fixed_{ctx.message.attachments[0].filename}'))
        zip_buffer.close()


def make_embed(multiworld):
    embed = discord.Embed(
        title='Multiworld Game',
        description='Here are the details of your multiworld game.',
        color=discord.Color.green()
    )
    embed.add_field(name="Game Token", value=multiworld['token'], inline=False)
    embed.add_field(name="Host", value=f"{c.MultiworldHostBase}:{multiworld['port']}", inline=False)
    if len(multiworld.get('players', [])) < 50:
        for idx, team in enumerate(multiworld.get('players', []), start=1):
            embed.add_field(name=f"Team #{idx}", value='\n'.join(team))

    return embed

def setup(bot):
    bot.add_cog(BontaMultiworld(bot))
