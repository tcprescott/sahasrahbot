import asyncio

from discord.ext import commands
import discord
import time

from alttprbot.exceptions import SahasrahBotException
from alttprbot.alttprgen.preset import get_preset, fetch_preset, PresetNotFoundException
from alttprbot.alttprgen.smz3multi import generate_multiworld
from ..util import checks


class SuperMetroidComboRandomizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def smz3(self, ctx):
        if ctx.invoked_subcommand is None:
            raise SahasrahBotException('Try providing a valid subcommand.  Use "$help smz3" for assistance.')

    @smz3.command()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def race(self, ctx, preset="normal"):
        seed, preset_dict = await get_preset(preset, randomizer='smz3', tournament=True)
        await ctx.send((
                f'Permalink: {seed.url}\n'
                f'Code: {seed.code}'
            ))

    @smz3.command()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def norace(self, ctx, preset="normal"):
        seed, preset_dict = await get_preset(preset, randomizer='smz3', tournament=False)
        await ctx.send((
                f'Permalink: {seed.url}\n'
                f'Code: {seed.code}'
            ))

    @commands.command()
    async def smz3multi(self, ctx, preset):
        await fetch_preset(preset, randomizer='smz3')

        embed = discord.Embed(
            title='SMZ3 Multiworld Game',
            description=(
                'A new multiworld game has been initiated, react with 👍 to join.\n'
                'When everyone is ready, the game creator can react with ✅ to create a session.'
            ),
            color=discord.Color.dark_blue()
        )
        embed.add_field(name="Status", value="Open for entry", inline=False)
        embed.add_field(name="Preset", value=preset, inline=False)
        embed.add_field(name="Players", value="No players yet.", inline=False)

        msg = await ctx.send(embed=embed)

        await msg.add_reaction('👍')
        await msg.add_reaction("✅")

        def add_check(reaction, user):
            return str(reaction.emoji) in ['👍', '✅'] and reaction.message.id == msg.id and not user.id == self.bot.user.id

        def remove_check(reaction, user):
            return str(reaction.emoji) == '👍' and reaction.message.id == msg.id and not user.id == self.bot.user.id

        timeout_start = time.time()
        close = False
        timeout = 900
        while time.time() < timeout_start + timeout and not close:
            try:
                pending_tasks = [
                    self.bot.wait_for('reaction_add', check=add_check),
                    self.bot.wait_for('reaction_remove', check=remove_check)
                ]
                done_tasks, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED, timeout=5)

                for task in pending_tasks:
                    task.cancel()

                for task in done_tasks:
                    reaction, user = await task
                    if str(reaction.emoji) == '✅' and user == ctx.author:
                        close = True
                    elif str(reaction.emoji) == '👍':
                        r = discord.utils.get(reaction.message.reactions, emoji='👍')
                        players = await r.users().flatten()
                        p_list = [p.name for p in players if not p.id == self.bot.user.id]
                        if len(p_list) > 0:
                            embed.set_field_at(2, name="Players", value='\n'.join(p_list))
                        else:
                            embed.set_field_at(2, name="Players", value='No players yet.')
            except asyncio.TimeoutError:
                pass
            embed.set_field_at(0, name="Status", value=f"Open for entry, auto-close in {round((timeout_start + timeout) - time.time(), 0)}s")
            await msg.edit(embed=embed)

        embed.set_field_at(0, name="Status", value="Game closed for entry.  Rolling...")
        await msg.edit(embed=embed)

        r = discord.utils.get(reaction.message.reactions, emoji='👍')
        players = await r.users().flatten()

        seed = await generate_multiworld(preset, [p.name for p in players if not p.id == self.bot.user.id], tournament=False)

        dm_embed = discord.Embed(
            title="SMZ3 Multiworld Game"
        )
        dm_embed.add_field(name="Players", value='\n'.join([p.name for p in players if not p.id == self.bot.user.id]), inline=False)
        dm_embed.add_field(name="Game Room", value=seed.url, inline=False)

        for player in players:
            if player.id == self.bot.user.id:
                continue
            try:
                await player.send(embed=dm_embed)
            except discord.HTTPException:
                await ctx.send(f"Unable to send DM to {player.mention}!")

        embed.set_field_at(0, name="Status", value="✅ Game started!  Check your DMs.")
        await msg.edit(embed=embed)

def setup(bot):
    bot.add_cog(SuperMetroidComboRandomizer(bot))
