import discord
from discord.ext import commands

from alttprbot.database import config
from alttprbot.exceptions import SahasrahBotException
from alttprbot.util import speedgaming
from alttprbot.alttprgen.mystery import generate_random_game
from alttprbot.alttprgen.preset import generate_preset, fetch_preset

from ..util import checks

# this module was only intended for the Main Tournament 2019
# we will probably expand this later to support other tournaments in the future


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if ctx.guild is None:
            return False

        if await config.get(ctx.guild.id, 'TournamentEnabled') == 'true':
            return True
        else:
            return False

    @commands.command(
        help="Generate a tournament race."
    )
    async def tourneyrace(self, ctx, episode_number):
        if await config.get(ctx.guild.id, 'TournamentAuditChannel'):
            audit_channel_id = int(await config.get(ctx.guild.id, 'TournamentAuditChannel'))
            audit_channel = discord.utils.get(
                ctx.guild.text_channels, id=audit_channel_id)
        else:
            audit_channel = None

        episode = await speedgaming.get_episode(int(episode_number))

        sg_event_slug = await config.get(ctx.guild.id, 'TournamentSGEventSlug')
        if sg_event_slug:
            if not episode['event']['slug'] == sg_event_slug:
                raise SahasrahBotException(
                    f'SG Episode ID provided is not an event for {sg_event_slug}')

        gentype = await config.get(ctx.guild.id, 'TournamentGameType')
        randomizer = await config.get(ctx.guild.id, 'TournamentRandomizer')

        if gentype == 'preset':
            preset = await config.get(ctx.guild.id, 'TournametPreset')
            if preset == False:
                raise SahasrahBotException(
                    'A preset is not set for this server\'s tournament.  Please contact Synack for help.')
            preset_dict = await fetch_preset(preset, randomizer)
            seed = await generate_preset(preset_dict, preset=preset, tournament=True, spoilers='off')

        elif gentype == 'mystery':
            weightset = await config.get(ctx.guild.id, 'TournamentWeightset')
            if weightset == False:
                raise SahasrahBotException(
                    'A weightset is not set for this server\'s tournament.  Please contact Synack for help.')
            seed = await generate_random_game(weightset=weightset, tournament=True, spoilers='mystery')
        else:
            raise SahasrahBotException(
                'TournamentGenType is not properly set for this tournament.  Please contact Synack for help.')

        players = episode['match1']['players']

        embed = await seed.embed(
            name=f"{players[0]['displayName']} vs. {players[1]['displayName']} - {episode_number}",
            emojis=self.bot.emojis
        )
        tournament_embed = await seed.tournament_embed(
            name=f"{players[0]['displayName']} vs. {players[1]['displayName']} - {episode_number}",
            notes="The permalink for this seed was sent via direct message to each runner.",
            emojis=self.bot.emojis
        )

        broadcast_channels = [
            a['name'] for a in episode['channels'] if not " " in a['name']]
        if len(broadcast_channels) > 0:
            twitch_channels = ', '.join(
                [f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels])
            tournament_embed.insert_field_at(
                0, name="Broadcast Channels", value=twitch_channels, inline=False)
            embed.insert_field_at(
                0, name="Broadcast Channels", value=twitch_channels, inline=False)

        if audit_channel:
            await audit_channel.send(embed=embed)
        else:
            await ctx.send(embed=embed)

        if await config.get(ctx.guild.id, 'TournamentCommentaryChannel'):
            commentary_channel_id = int(await config.get(ctx.guild.id, 'TournamentCommentaryChannel'))
            commentary_channel = discord.utils.get(
                ctx.guild.text_channels, id=commentary_channel_id)
            await commentary_channel.send(embed=tournament_embed)

        for player in players:
            try:
                if not player.get('discordId', '') == '':
                    member = ctx.guild.get_member(int(player['discordId']))
                else:
                    member = await commands.MemberConverter().convert(ctx, player['discordTag'])
                await member.send(embed=embed)
            except Exception:
                if audit_channel:
                    await audit_channel.send(f"Unable to send DM to {player['displayName']}")
                await ctx.send(f"Unable to send DM to {player['displayName']}")


def setup(bot):
    bot.add_cog(Tournament(bot))
