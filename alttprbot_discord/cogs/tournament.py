import random

import discord
from discord import app_commands
from discord.ext import commands

import config
# from alttprbot_discord.util import alttpr_discord
from alttprbot import models
# Must be imported before alttprbot.tournament.alttpr, which is circular with tournament.core otherwise.
from alttprbot import tournaments  # noqa: F401
from alttprbot.tournament import alttpr

# TODO: use asyncio.semaphore() to limit the number of concurrent tasks

MAIN_TOURNAMENT_SERVERS = list(map(int, config.MAIN_TOURNAMENT_SERVERS.split(',')))
CC_TOURNAMENT_SERVERS = list(map(int, config.CC_TOURNAMENT_SERVERS.split(',')))
CC_TOURNAMENT_AUDIT_CHANNELS = int(config.CC_TOURNAMENT_AUDIT_CHANNELS)

MAIN_TOURNAMENT_ADMIN_ROLE_ID = 523276397679083520 if config.DEBUG else 334796844750209024
CC_TOURNAMENT_ADMIN_ROLE_ID = 523276397679083520 if config.DEBUG else 503724516854202370


class ChallengeCupDeleteHistoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Delete from Tournament History', style=discord.ButtonStyle.danger,
                       custom_id='sahabot:delete_history')
    async def delete_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to delete history.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        await interaction.user.send(f"Are you sure you want to delete the history of this race?\n\n{embed.title}",
                                    view=ChallengeCupDeleteHistoryConfirmationView(message=interaction.message))
        await interaction.response.send_message("Check your DMs.", ephemeral=True)


class ChallengeCupDeleteHistoryConfirmationView(discord.ui.View):
    def __init__(self, message: discord.Message):
        super().__init__(timeout=300)
        self.message = message

    @discord.ui.button(label='Confirm Delete History', style=discord.ButtonStyle.danger)
    async def delete_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        message_id = self.message.id

        await models.TournamentPresetHistory.filter(
            episode_id=message_id,
            event_slug='cc2023'
        ).delete()
        await self.message.add_reaction('🗑️')

        # disable buttons
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        await interaction.response.send_message("History deleted.")


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(ChallengeCupDeleteHistoryView())
            self.persistent_views_added = True

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if ctx.guild is None:
            return False

        if await ctx.guild.config_get('TournamentEnabled') == 'true':
            return True
        else:
            return False

    # @app_commands.command(description="Generate an ALTTPR practice seed from an SG Episode that's already been submitted.")
    # async def practice(self, interaction: discord.Interaction, episode_id: int):
    #     await interaction.response.defer()
    #     tournament_game = await models.TournamentGames.get_or_none(episode_id=episode_id)
    #     if tournament_game is None:
    #         await interaction.response.send_message("That episode has not been submitted yet.", ephemeral=True)
    #         return

    #     settings = tournament_game.settings

    #     seed = await alttpr_discord.ALTTPRDiscord.generate(settings=settings, endpoint='/api/customizer')  # TODO: don't hardcode endpoint
    #     embed = await seed.embed(emojis=self.bot.emojis)

    #     await interaction.followup.send(embed=embed)

    # @app_commands.command(description="Generate a randomizer seed for the ALTTPR Main Tournament 2024.")
    # async def 4(self, interaction: discord.Interaction, player1: discord.Member, player2: discord.Member):
    #     await interaction.response.defer()
    #     seed, preset, deck = await alttpr.roll_seed([player1, player2])

    #     embed = await seed.embed(emojis=self.bot.emojis)
    #     embed.insert_field_at(0, name="Preset", value=preset, inline=False)
    #     if deck:
    #         embed.insert_field_at(1, name="Deck", value="\n".join([f"**{p}**: {c}" for p, c in deck.items()]), inline=False)

    #     await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Generate a randomizer seed for the 2023 challenge cup.")
    @app_commands.guilds(*CC_TOURNAMENT_SERVERS)
    async def cc2023(self, interaction: discord.Interaction, opponent: discord.Member,
                     on_behalf_of: discord.Member = None, player3: discord.Member = None,
                     player4: discord.Member = None):

        if on_behalf_of and interaction.guild.get_role(CC_TOURNAMENT_ADMIN_ROLE_ID) not in interaction.user.roles:
            await interaction.response.send_message(
                "You must be a member of the Challenge Cup admin team to roll a seed on someone else's behalf..")
            return

        if (player3 or player4) and interaction.guild.get_role(
                CC_TOURNAMENT_ADMIN_ROLE_ID) not in interaction.user.roles:
            await interaction.response.send_message(
                "You must be a member of the Challenge Cup admin team to roll a seed with more than 2 players.")
            return

        if interaction.user == opponent:
            await interaction.response.send_message("You can't race yourself.", ephemeral=True)
            return

        if on_behalf_of is None:
            on_behalf_of = interaction.user

        if opponent.bot or on_behalf_of.bot:
            await interaction.response.send_message("You can't race a bot.", ephemeral=True)
            return

        players = [opponent, on_behalf_of]
        if player3:
            players.append(player3)
        if player4:
            players.append(player4)

        await interaction.response.defer()
        # embed = await self.generate_deck_seed(players, "cc2023")

        msg_id = None

        if CC_TOURNAMENT_AUDIT_CHANNELS:
            channel = self.bot.get_channel(CC_TOURNAMENT_AUDIT_CHANNELS)
            msg = await channel.send("Generating...")
            msg_id = msg.id

        seed, preset, deck = await alttpr.roll_seed(players, event_slug="cc2023", episode_id=msg_id)

        embed = await seed.embed(emojis=self.bot.emojis, include_settings=False)
        embed.insert_field_at(0, name="Preset", value=preset, inline=False)
        if deck:
            embed.insert_field_at(1, name="Deck", value="\n".join([f"**{p}**: {c}" for p, c in deck.items()]),
                                  inline=False)

        embed.title = " vs. ".join([p.display_name for p in players])
        embed.description = " vs. ".join([p.mention for p in players])

        for player in players:
            await player.send(embed=embed)

        if CC_TOURNAMENT_AUDIT_CHANNELS:
            await msg.edit(content="Sent to players.", embed=embed, view=ChallengeCupDeleteHistoryView())

        await interaction.followup.send("Seed successfully sent to DM.")

    @app_commands.command(
        description="Generate a hypothetical deck for a match.  This does not generate a seed or write to history.")
    @app_commands.guilds(*CC_TOURNAMENT_SERVERS, *MAIN_TOURNAMENT_SERVERS)
    @app_commands.choices(
        event_slug=[
            app_commands.Choice(name="cc2024", value="cc2024"),
            app_commands.Choice(name="alttpr2024", value="alttpr2024"),
        ]
    )
    async def tournament_deck(self, interaction: discord.Interaction, opponent: discord.Member,
                              on_behalf_of: discord.Member = None, event_slug: str = None):
        if on_behalf_of is None:
            on_behalf_of = interaction.user

        if interaction.user == opponent:
            await interaction.response.send_message("You must specify two different players.", ephemeral=True)
            return

        if opponent.bot or on_behalf_of.bot:
            await interaction.response.send_message("You cannot specify a bot as a player.", ephemeral=True)
            return

        if event_slug is None:
            if interaction.guild.id in CC_TOURNAMENT_SERVERS:
                event_slug = "cc2023"
            elif interaction.guild.id in MAIN_TOURNAMENT_SERVERS:
                event_slug = "alttpr2024"
            else:
                await interaction.response.send_message("You must specify an event slug.", ephemeral=True)
                return

        deck = await alttpr.generate_deck([opponent, on_behalf_of], event_slug=event_slug)
        preset = random.choices(list(deck.keys()), weights=list(deck.values()))[0]
        embed = discord.Embed(
            title=f"{opponent.display_name} vs. {on_behalf_of.display_name}",
            description=f"{opponent.mention} vs. {on_behalf_of.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Deck", value="\n".join([f"**{p}**: {c}" for p, c in deck.items()]), inline=False)
        embed.add_field(name="In this hypothetical matchup, this mode was drawn:", value=preset, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tournament(bot))
