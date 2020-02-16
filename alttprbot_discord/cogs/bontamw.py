from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.util import http
from config import Config as c

MULTIWORLDS = {}

class BontaMultiworld(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def mwhost(self, ctx):
        if not ctx.message.attachments:
            raise SahasrahBotException('Must attach a multidata file.')

        data = {
            'multidata_url': ctx.message.attachments[0].url,
            'admin': ctx.author.id
        }
        multiworld = await http.request_json_post(url='http://localhost:5000/game', data=data, returntype='json')

        await ctx.send(
            f"Game Token: {multiworld['token']}\n"
            f"Host: {c.MultiworldHostBase}:{multiworld['port']}"
        )

    @commands.command()
    async def mwmsg(self, ctx, token, msg):
        result = await http.request_generic(url=f'http://localhost:5000/game/{token}', method='get', returntype='json')

        if not result['admin'] == ctx.author.id:
            raise SahasrahBotException('You must be the creater of the game to send messages to it.')

        data = {
            'msg': msg
        }
        await http.request_json_put(url=f'http://localhost:5000/game/{token}/msg', data=data)

    @commands.command()
    @commands.is_owner()
    async def mwresume(self, ctx, token, port):
        data = {
            'token': token,
            'port': port,
            'admin': ctx.author.id
        }
        multiworld = await http.request_json_post(url='http://localhost:5000/game', data=data, returntype='json')

        await ctx.send(
            f"Game Token: {multiworld['token']}\n"
            f"Host: {c.MultiworldHostBase}:{multiworld['port']}"
        )

def setup(bot):
    bot.add_cog(BontaMultiworld(bot))
