import discord
from discord.ext import commands
from alttprbot import models
from typing import List
import pyrankvote
import os
import io

APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')


async def calculate_results(election: models.RankedChoiceElection):
    await election.fetch_related('candidates')
    await election.fetch_related('votes', 'votes__candidate')
    candidates = {candidate.name:pyrankvote.Candidate(candidate.name) for candidate in election.candidates}
    voters = list(set([a.user_id for a in election.votes]))
    ballots = []
    for voter in voters:
        votes: List[models.RankedChoiceVotes] = [v for v in election.votes if v.user_id == voter]
        votes.sort(key=lambda x: x.rank)
        ballot = pyrankvote.Ballot([candidates[v.candidate.name] for v in votes])
        ballots.append(ballot)

    election_result = pyrankvote.single_transferable_vote(candidates=candidates.values(), ballots=ballots, number_of_seats=election.seats) # TODO: make this a variable

    winners = election_result.get_winners()

    for winner in winners:
        winner_candidate = next((c for c in election.candidates if c.name == winner.name), None)
        if winner_candidate:
            winner_candidate.winner = True
            await winner_candidate.save()

    election.results = str(election_result)
    await election.save()

    return

def create_embed(election: models.RankedChoiceElection):
    embed = discord.Embed(title=election.title, description=election.description)
    embed.add_field(name="Seats up for election", value=election.seats, inline=False)
    embed.add_field(name="Candidates", value="\n".join([f"{i+1}. {candidate.name} {'✅' if candidate.winner else ''}" for i, candidate in enumerate(election.candidates)]), inline=False)
    if election.private:
        voter_list = []
        for voter in election.authorized_voters:
            if election.show_vote_count:
                if [vote for vote in election.votes if vote.user_id == voter.user_id]:
                    suffix = " ✅"
                else:
                    suffix = " ❌"
            else:
                suffix = ""

            voter_list.append(f"<@{voter.user_id}>{suffix}")
        embed.add_field(name="Authorized Voters", value="\n".join(voter_list), inline=False)
    embed.add_field(name="Vote URL", value=f"{APP_URL}/ranked_choice/{election.id}", inline=False)
    embed.add_field(name="Owner", value=f"<@{election.owner_id}>", inline=False)
    embed.add_field(name="Status", value="Open" if election.active else "Closed", inline=False)
    embed.set_footer(text=f"ID: {election.id}")
    return embed

async def refresh_election_post(election: models.RankedChoiceElection, bot: commands.Bot):
    await election.fetch_related('candidates')
    await election.fetch_related('authorized_voters')
    await election.fetch_related('votes')

    guild = bot.get_guild(election.guild_id)
    message = await guild.fetch_message(election.message_id)
    if election.results:
        file = [discord.File(io.StringIO(election.results), filename="results.txt")]
        await message.edit(embed=create_embed(election), attachments=file)
    else:
        await message.edit(embed=create_embed(election))