import discord
from discord.ext import commands

from alttprbot.database import srlnick
from alttprbot.tournament import main, secondary
from alttprbot.util import speedgaming
from config import Config as c

from ..util import checks

# this module was only intended for the Main Tournament 2019
# we will probably expand this later to support other tournaments in the future

class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if ctx.guild is None:
            return False
        if ctx.guild.id in c.Tournament:
            return True
        else:
            return False

    @commands.command()
    @commands.has_any_role('Admin','Admins','Bot Admin')
    async def ccloadreg(self, ctx):
        if c.Tournament[ctx.guild.id]['tournament'] == 'secondary':
            await secondary.loadnicks(ctx)
        else:
            raise Exception('This command only works for the Challenge Cup.')

    @commands.command(
        help="Generate a tournament race.",
        aliases=['restreamrace', 'tournyrace', 'tounyrace']
    )
    @checks.has_any_channel('testing', 'console', 'lobby', 'restreamers', 'sg-races', 'bot-console', 'bot-testing', 'bot-commands')
    async def tourneyrace(self, ctx, episode_number):
        logging_channel = discord.utils.get(ctx.guild.text_channels, id=c.Tournament[ctx.guild.id]['logging_channel'])

        if c.Tournament[ctx.guild.id]['tournament'] == 'main':
            try:
                seed, game_number, players = await main.generate_game(episode_number, ctx.guild.id)
            except main.SettingsSubmissionNotFoundException as e:
                await dm_all_players_sg(ctx, episode_number, f"Settings submission not found at <https://docs.google.com/spreadsheets/d/1GHBnuxdLgBcx4llvHepQjwd8Q1ASbQ_4J8ubblyG-0c/edit#gid=941774009>.  Please submit settings at <http://bit.ly/2Dbr9Kr> for episode `{episode_number}`!  Once complete, re-run `$tourneyrace` command or contact your setup helper to have command re-ran.")
                raise
            except main.InvalidSettingsException as e:
                await dm_all_players_sg(ctx, episode_number, f"Settings submitted for episode `{episode_number}` are invalid!  Please contact a tournament administrator for assistance.")
                raise
        elif c.Tournament[ctx.guild.id]['tournament'] == 'secondary':
            seed, game_number, players = await secondary.generate_game(episode_number, ctx.guild.id)
        else:
            raise Exception('This should not have happened.  Ping Synack.')

        embed = await seed.embed(
            name=f"{players[0]['displayName']} vs. {players[1]['displayName']} - {game_number} - {episode_number}",
            emojis=self.bot.emojis
        )
        tournament_embed = await seed.tournament_embed(
            name=f"{players[0]['displayName']} vs. {players[1]['displayName']} - {game_number} - {episode_number}",
            notes="The permalink for this seed was sent via direct message to each runner.",
            emojis=self.bot.emojis
        )

        if c.Tournament[ctx.guild.id]['tournament'] == 'main' and 'commentary_channel' in c.Tournament[ctx.guild.id]:
            episode = await speedgaming.get_episode(int(episode_number))
            broadcast_channels = []
            for channel in episode['channels']:
                if not channel['name'] == "No Stream":
                    broadcast_channels.append(channel['name'])
            if len(broadcast_channels) > 0:
                commentary_channel = discord.utils.get(ctx.guild.text_channels, id=c.Tournament[ctx.guild.id]['commentary_channel'])
                tournament_embed.insert_field_at(0, name="Broadcast Channels", value=f"*{', '.join(broadcast_channels)}*", inline=False)
                embed.insert_field_at(0, name="Broadcast Channels", value=f"*{', '.join(broadcast_channels)}*", inline=False)
                await commentary_channel.send(embed=tournament_embed)

        await logging_channel.send(embed=embed)
        await ctx.send(embed=tournament_embed)

        for player in players:
            try:
                if not player.get('discordId', '') == '':
                    member = ctx.guild.get_member(int(player['discordId']))
                else:
                    member = await commands.MemberConverter().convert(ctx, player['discordTag'])
                await member.send(embed=embed)
            except discord.HTTPException:
                await logging_channel.send(f"@here Unable to send DM to {player['displayName']}")
                await ctx.send(f"Unable to send DM to {player['displayName']}")


    @commands.command()
    @commands.has_any_role('Admin','Admins','Bot Admin')
    async def loadroles(self, ctx, role: discord.Role, names):
        namelist = names.splitlines()

        for name in namelist:
            discord_users = await srlnick.get_discord_id(name)
            if discord_users is False:
                continue
            else:
                for discord_user in discord_users:
                    member = ctx.guild.get_member(discord_user['discord_user_id'])
                    if member is not None:
                        await member.add_roles(role)


async def dm_all_players_sg(ctx, episode_number, msg):
    episode = await speedgaming.get_episode(int(episode_number))
    for player in episode['match1']['players']:
        try:
            if not player.get('discordId', '') == '':
                member = ctx.guild.get_member(int(player['discordId']))
            else:
                member = await commands.MemberConverter().convert(ctx, player['discordTag'])
            await member.send(msg)
        except:
            pass


def setup(bot):
    bot.add_cog(Tournament(bot))
