from discord.ext import commands
from alttprbot.exceptions import SahasrahBotException

from alttprbot.database import srlnick
from alttprbot_srl import nick_verifier

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help="Register your SRL nick with SahasrahBot."
    )
    async def srl(self, ctx, nick):
        user = await nick_verifier.get_irc_user(nick)
        if user:
            if await nick_verifier.send_key(ctx.author.id, nick):
                await ctx.send("A private message has been sent to you in SRL by SahasrahBot.  Please click the link in the message sent to you.\n\nIf you have not received this message, please contact Synack for assistance.\n\nThanks!")
        else:
            raise SahasrahBotException("The user specified is not logged into SRL. Please ensure your logged into SRL and identified by NickServ.")

    @commands.command(
        help="Register your Twitch name with SahasrahBot."
    )
    async def twitch(self, ctx, twitch):
        await srlnick.insert_twitch_name(ctx.author.id, twitch)

    @commands.command(
        help="List the nicknames registered with SahasrahBot."
    )
    async def getnick(self, ctx):
        nick = await srlnick.get_nicknames(ctx.author.id)
        if nick:
            await ctx.send(f"Your currently registered nickname for SRL is `{nick[0]['srl_nick']}`\nYour currently registered nickname for Twitch is `{nick[0]['twitch_name']}`")
        else:
            await ctx.send("You currently do not have any nicknames registered with this bot.  Use the command `$srl yournick` and `$twitch yournick` to do that!")

    @commands.command()
    async def srlinfo(self, ctx, srl_nick):
        await ctx.send(await nick_verifier.get_irc_user(srl_nick))

def setup(bot):
    bot.add_cog(Nickname(bot))
