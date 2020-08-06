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

    @commands.group()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def sm(self, ctx):
        if ctx.invoked_subcommand is None:
            raise SahasrahBotException('Try providing a valid subcommand.  Use "$help smz3" for assistance.')

    @sm.command(
        name='race'
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def sm_race(self, ctx, preset="normal"):
        seed, preset_dict = await get_preset(preset, randomizer='sm', tournament=True)
        await ctx.send((
                f'Permalink: {seed.url}\n'
                f'Code: {seed.code}'
            ))

    @sm.command(
        name='norace'
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def sm_norace(self, ctx, preset="normal"):
        seed, preset_dict = await get_preset(preset, randomizer='sm', tournament=False)
        await ctx.send((
                f'Permalink: {seed.url}\n'
                f'Code: {seed.code}'
            ))

    @commands.command(
        help='Initiates an SMZ3 Multiworld Game.  The game will auto-close and roll 30 minutes later.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/smz3>.',
        brief='Initiate a SMZ3 Multiworld Game.',
    )
    async def smz3multi(self, ctx, preset):
        await self.handle_multiworld(ctx, preset, randomizer='smz3')

    @commands.command(
        help='Initiates an SM Multiworld Game.  The game will auto-close and roll 30 minutes later.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/sm>.',
        brief='Initiate a SM Multiworld Game.',
    )
    async def smmulti(self, ctx, preset):
        await self.handle_multiworld(ctx, preset, randomizer='sm')

    async def handle_multiworld(self, ctx, preset, randomizer):
        await fetch_preset(preset, randomizer=randomizer)

        embed = discord.Embed(
            title=f'{randomizer.upper()} Multiworld Game',
            description=(
                'A new multiworld game has been initiated, react with 👍 to join.\n'
                'When everyone is ready, the game creator can react with ✅ to create a session.\n'
                'The game creator can react with ❌ to cancel this game.'
            ),
            color=discord.Color.dark_blue()
        )
        embed.add_field(name="Status", value="👍 Open for entry", inline=False)
        embed.add_field(name="Preset", value=f"[{preset.lower()}](https://github.com/tcprescott/sahasrahbot/blob/master/presets/{randomizer.lower()}/{preset.lower()}.yaml)", inline=False)
        embed.add_field(name="Players", value="No players yet.", inline=False)

        msg = await ctx.send(embed=embed)

        await msg.add_reaction('👍')
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def add_check(reaction, user):
            return str(reaction.emoji) in ['👍', '✅', '❌'] and reaction.message.id == msg.id and not user.id == self.bot.user.id

        def remove_check(reaction, user):
            return str(reaction.emoji) == '👍' and reaction.message.id == msg.id and not user.id == self.bot.user.id

        timeout_start = time.time()
        close = False
        roll = True
        timeout = 1800
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
                    if str(reaction.emoji) == '❌' and user == ctx.author:
                        close = True
                        roll = False
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
            embed.set_field_at(0, name="Status", value=f"👍 Open for entry, auto-close in {round((timeout_start + timeout) - time.time(), 0)}s")
            await msg.edit(embed=embed)

        if not roll:
            embed.set_field_at(0, name="Status", value="❌ Cancelled.")
            await msg.edit(embed=embed)
            return

        embed.set_field_at(0, name="Status", value="⌚ Game closed for entry.  Rolling...")
        await msg.edit(embed=embed)

        r = discord.utils.get(reaction.message.reactions, emoji='👍')
        reaction_users = await r.users().flatten()

        if len(reaction_users) < 3:
            embed.set_field_at(0, name="Status", value="❌ Too few players.  Cancelled.")
            await msg.edit(embed=embed)
            raise SahasrahBotException("You must have at least two players to create a multiworld.")

        players = [p for p in players if not p.id == self.bot.user.id]

        seed = await generate_multiworld(preset, [p.name for p in players], tournament=False, randomizer=randomizer)

        dm_embed = discord.Embed(
            title=f'{randomizer.upper()} Multiworld Game'
        )
        dm_embed.add_field(name="Players", value='\n'.join([p.name for p in players]), inline=False)
        dm_embed.add_field(name="Game Room", value=seed.url, inline=False)

        for player in players:
            try:
                await player.send(embed=dm_embed)
            except discord.HTTPException:
                await ctx.send(f"Unable to send DM to {player.mention}!")

        embed.set_field_at(0, name="Status", value="✅ Game started!  Check your DMs.")
        await msg.edit(embed=embed)

def setup(bot):
    bot.add_cog(SuperMetroidComboRandomizer(bot))
