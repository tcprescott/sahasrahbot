"""Discord rendering for ranked-choice elections.

Builds the election embed and refreshes the posted election message. These are
the presentation-tier concerns split out of the old ``alttprbot.util.rankedchoice``
module; tabulation/persistence live in :class:`RankedChoiceService`.
"""

import io

import discord

import config

APP_URL = config.APP_URL


def create_embed(election):
    embed = discord.Embed(title=election.title, description=election.description)
    embed.add_field(name="Seats up for election", value=election.seats, inline=False)
    embed.add_field(name="Candidates", value="\n".join(
        [f"{i + 1}. {candidate.name} {'✅' if candidate.winner else ''}" for i, candidate in
         enumerate(election.candidates)]), inline=False)
    if election.private:
        embed.add_field(name="Authorized Voters Role", value=f'<@&{election.voter_role_id}>', inline=False)
    embed.add_field(name="Vote URL", value=f"{APP_URL}/ranked_choice/{election.id}", inline=False)
    embed.add_field(name="Owner", value=f"<@{election.owner_id}>", inline=False)
    embed.add_field(name="Status", value="Open" if election.active else "Closed", inline=False)
    embed.set_footer(text=f"ID: {election.id}")
    return embed


async def refresh_election_post(election, bot):
    await election.fetch_related('candidates')
    await election.fetch_related('authorized_voters')
    await election.fetch_related('votes')

    channel = bot.get_channel(election.channel_id)
    message = await channel.fetch_message(election.message_id)
    if election.results:
        file = [discord.File(io.StringIO(election.results), filename="results.txt")]
        await message.edit(embed=create_embed(election), attachments=file)
    else:
        await message.edit(embed=create_embed(election))
