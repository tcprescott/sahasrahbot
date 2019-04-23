from config import Config

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # get/set configuration values, only the server administrator should be able to set these
    @commands.group(name='config')
    @commands.has_permissions(administrator=True)
    async def config_func(self, ctx):
        pass

    @config_func.command()
    async def set(self, ctx, parameter, value):
        await ctx.message.add_reaction('⌚')

        loop = asyncio.get_event_loop()
        lbdb = db.LeagueBotDatabase(loop)
        await lbdb.connect()
        await lbdb.set_config(ctx.guild.id, parameter, value)
        await lbdb.close()

        await ctx.message.add_reaction('👍')
        await ctx.message.remove_reaction('⌚',ctx.bot.user)

    @config_func.command()
    async def get(self, ctx, parameter):
        await ctx.message.add_reaction('⌚')


        loop = asyncio.get_event_loop()
        lbdb = db.LeagueBotDatabase(loop)
        await lbdb.connect()
        result = await lbdb.get_config(ctx.guild.id, parameter)
        await ctx.send(result['value'])
        await lbdb.close()

        await ctx.message.add_reaction('👍')
        await ctx.message.remove_reaction('⌚',ctx.bot.user)

def setup(bot):
    bot.add_cog(Admin(bot))