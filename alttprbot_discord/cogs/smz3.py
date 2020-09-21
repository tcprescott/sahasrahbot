from discord.ext import commands
import discord

from alttprbot.alttprgen.preset import get_preset, fetch_preset
from alttprbot.alttprgen.smz3multi import generate_multiworld
from alttprbot.database import smz3_multiworld
from ..util import checks


class SuperMetroidComboRandomizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        mw = await smz3_multiworld.fetch(payload.message_id, status="STARTED")
        if mw and payload.message_id == mw.get('message_id') and not payload.user_id == self.bot.user.id:
            emoji = str(payload.emoji)
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if emoji == '👍':
                await self.update_mw_message(mw, message)
            elif emoji == '✅':
                await self.close_mw(mw, message, payload.member)
            elif emoji == '❌':
                await self.cancel_mw(mw, message, payload.member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        mw = await smz3_multiworld.fetch(payload.message_id, status="STARTED")
        if mw and payload.message_id == mw.get('message_id') and not payload.user_id == self.bot.user.id:
            emoji = str(payload.emoji)
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if emoji == '👍':
                await self.update_mw_message(mw, message)

    @commands.group()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def smz3(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Please specify a subcommand!')

    @smz3.command(
        help='Generates a SMZ3 Race.\nThis game will not have a spoiler log.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/smz3>.',
        brief='Generates a SMZ3 Race.'
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def race(self, ctx, preset):
        seed, preset_dict = await get_preset(preset, randomizer='smz3', tournament=True)
        await ctx.send((
            f'Permalink: {seed.url}\n'
            f'Code: {seed.code}'
        ))

    @smz3.command(
        help='Generates a SMZ3 Game.\nThis game will have a spoiler log.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/smz3>.',
        brief='Generates a SMZ3 Game.'
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def norace(self, ctx, preset):
        seed, preset_dict = await get_preset(preset, randomizer='smz3', tournament=False)
        await ctx.send((
            f'Permalink: {seed.url}\n'
            f'Code: {seed.code}'
        ))

    @smz3.command(
        name='multi',
        help='Initiates an SMZ3 Multiworld Game.  The game will auto-close and roll 30 minutes later.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/smz3>.',
        brief='Initiate a SMZ3 Multiworld Game.',
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def multi(self, ctx, preset):
        await self.init_mw(ctx, preset, randomizer='smz3')

    @commands.group()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def sm(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Please specify a subcommand!')

    @sm.command(
        name='race',
        help='Generates a SM Race.\nThis game will not have a spoiler log.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/sm>.',
        brief='Generates a SM Race.'
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def sm_race(self, ctx, preset):
        seed, preset_dict = await get_preset(preset, randomizer='sm', tournament=True)
        await ctx.send((
            f'Permalink: {seed.url}\n'
            f'Code: {seed.code}'
        ))

    @sm.command(
        name='norace',
        help='Generates a SM Game.\nThis game will have a spoiler log.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/sm>.',
        brief='Generates a SM Game.'
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def sm_norace(self, ctx, preset):
        seed, preset_dict = await get_preset(preset, randomizer='sm', tournament=False)
        await ctx.send((
            f'Permalink: {seed.url}\n'
            f'Code: {seed.code}'
        ))

    @sm.command(
        name='multi',
        help='Initiates an SM Multiworld Game.  The game will auto-close and roll 30 minutes later.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/sm>.',
        brief='Initiate a SM Multiworld Game.',
    )
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def sm_multi(self, ctx, preset):
        await self.init_mw(ctx, preset, randomizer='sm')

    @commands.command(
        help='Initiates an SMZ3 Multiworld Game.  The game will auto-close and roll 30 minutes later.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/smz3>.',
        brief='Initiate a SMZ3 Multiworld Game.',
        hidden=True,
    )
    async def smz3multi(self, ctx, preset):
        await self.init_mw(ctx, preset, randomizer='smz3')

    @commands.command(
        help='Initiates an SM Multiworld Game.  The game will auto-close and roll 30 minutes later.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/sm>.',
        brief='Initiate a SM Multiworld Game.',
        hidden=True,
    )
    async def smmulti(self, ctx, preset):
        await self.init_mw(ctx, preset, randomizer='sm')

    async def init_mw(self, ctx, preset, randomizer):
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
        embed.add_field(
            name="Preset", value=f"[{preset.lower()}](https://github.com/tcprescott/sahasrahbot/blob/master/presets/{randomizer.lower()}/{preset.lower()}.yaml)", inline=False)
        embed.add_field(name="Players", value="No players yet.", inline=False)

        msg = await ctx.send(embed=embed)

        await smz3_multiworld.insert(
            message_id=msg.id,
            owner_id=ctx.author.id,
            randomizer=randomizer,
            preset=preset,
            status="STARTED",
        )

        await msg.add_reaction('👍')
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

    async def update_mw_message(self, mw, message):
        embed = message.embeds[0]
        r = discord.utils.get(message.reactions, emoji='👍')
        players = await r.users().flatten()
        p_list = [p.name for p in players if not p.id == self.bot.user.id]
        if len(p_list) > 0:
            embed.set_field_at(
                2, name="Players", value='\n'.join(p_list))
        else:
            embed.set_field_at(
                2, name="Players", value='No players yet.')

        await message.edit(embed=embed)

    async def close_mw(self, mw, message, member):
        if not mw['owner_id'] == member.id:
            await message.remove_reaction('✅', member)
            return

        embed = message.embeds[0]
        embed.set_field_at(
            0, name="Status", value="⌚ Game closed for entry.  Rolling...")
        await message.edit(embed=embed)

        r = discord.utils.get(message.reactions, emoji='👍')
        reaction_users = await r.users().flatten()

        players = [p for p in reaction_users if not p.id == self.bot.user.id]

        if len(players) < 2:
            await message.channel.send(f"{member.mention} You must have at least two players to create a multiworld.  If you wish to cancel this multiworld, click ❌.")
            embed.set_field_at(
                0, name="Status", value="👍 Open for entry")
            await message.remove_reaction('✅', member)
            await message.edit(embed=embed)
            return

        seed = await generate_multiworld(mw['preset'], [p.name for p in players], tournament=False, randomizer=mw['randomizer'])

        dm_embed = discord.Embed(
            title=f"{mw['randomizer'].upper()} Multiworld Game"
        )
        dm_embed.add_field(name="Players", value='\n'.join(
            [p.name for p in players]), inline=False)
        dm_embed.add_field(name="Game Room", value=seed.url, inline=False)

        for player in players:
            try:
                await player.send(embed=dm_embed)
            except discord.HTTPException:
                await message.channel.send(f"Unable to send DM to {player.mention}!")

        embed.set_field_at(
            0, name="Status", value="✅ Game started!  Check your DMs.")
        await message.edit(embed=embed)
        await smz3_multiworld.update_status(message.id, "CLOSED")

    async def cancel_mw(self, mw, message, member):
        if not mw['owner_id'] == member.id:
            await message.remove_reaction('❌', member)
            return

        embed = message.embeds[0]
        embed.set_field_at(0, name="Status", value="❌ Cancelled.")
        await message.edit(embed=embed)
        await smz3_multiworld.update_status(message.id, "CANCELLED")


def setup(bot):
    bot.add_cog(SuperMetroidComboRandomizer(bot))
