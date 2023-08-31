from quart import Blueprint, render_template, request, abort
from quart_discord import requires_authorization
import tortoise.exceptions

from alttprbot import models
from alttprbot.util import rankedchoice
from alttprbot_discord.bot import discordbot

from discord.errors import NotFound

from ..api import discord

# TODO: add a way to resubmit votes (low priority)
# TODO: client-side verification that ranked choices are unique
# TODO: the entire Discord-side of this need to be written
# TODO: deduplicate code between presentation and submission

ranked_choice_blueprint = Blueprint('ranked_choice', __name__)


@ranked_choice_blueprint.route('/ranked_choice/<int:election_id>', methods=['GET'])
@requires_authorization
async def get_ballot(election_id: int):
    user = await discord.fetch_user()
    logged_in = True

    try:
        election = await models.RankedChoiceElection.get(id=election_id)
    except tortoise.exceptions.DoesNotExist:
        return abort(404, "Election not found")

    if not election.active:
        return abort(404, "Election is inactive.")

    if election.private:
        guild = await discordbot.fetch_guild(election.guild_id)
        voter_role = guild.get_role(election.voter_role_id)
        try:
            member = await guild.fetch_member(user.id)
        except NotFound:
            return abort(403, "Unable to find you in the server.  Please contact Synack if you believe this is an error.")

        if voter_role not in member.roles:
            return abort(403, "You are not authorized to vote in this election.")

    await election.fetch_related('candidates')

    existing_votes = await election.votes.filter(user_id=user.id)
    if existing_votes:
        # await abort(403, "You have already voted in this election.  Please contact Synack if you need to change your vote.")
        return await render_template('ranked_choice_submit.html', election=election, votes=existing_votes, logged_in=logged_in, user=user)

    return await render_template('ranked_choice_vote.html', election=election, logged_in=logged_in, user=user)


@ranked_choice_blueprint.route('/ranked_choice/<int:election_id>', methods=['POST'])
@requires_authorization
async def submit_ballot(election_id: int):
    user = await discord.fetch_user()
    logged_in = True

    try:
        election = await models.RankedChoiceElection.get(id=election_id)
    except tortoise.exceptions.DoesNotExist:
        return abort(404, "Election not found")

    if not election.active:
        return abort(404, "Election is inactive.")

    if election.private:
        guild = await discordbot.fetch_guild(election.guild_id)
        voter_role = guild.get_role(election.voter_role_id)
        member = await guild.fetch_member(user.id)
        if voter_role not in member.roles:
            return abort(403, "You are not authorized to vote in this election.")

    await election.fetch_related('candidates')

    existing_votes = await election.votes.filter(user_id=user.id)
    if existing_votes:
        await abort(403, "You have already voted in this election.  Please contact Synack if you need to change your vote.")

    payload = await request.form

    if dupcheck([v for v in payload.values() if not v == '']):  # this is broken and we're not sure why
        return await abort(400, "Each candidate must have a unique rank.")

    if dupcheck(list(payload.keys())):
        return await abort(400, "You can only vote for each candidate once.  This should not have happened.  Please contact Synack.")

    votes = []

    for key, value in payload.items():
        if not key.startswith('candidate_'):
            continue

        candidate_id = int(remove_prefix(key, 'candidate_'))
        if value == '':
            continue

        try:
            rank = int(value)
        except ValueError:
            continue

        candidate = next((c for c in election.candidates if c.id == candidate_id), None)
        if not candidate:
            return abort(400, "Invalid candidate")

        votes.append(models.RankedChoiceVotes(
            election=election,
            candidate=candidate,
            user_id=user.id,
            rank=rank
        ))

    votes.sort(key=sort_rank)
    await models.RankedChoiceVotes.bulk_create(votes)

    await rankedchoice.refresh_election_post(election, discordbot)

    return await render_template('ranked_choice_submit.html', election=election, votes=votes, logged_in=logged_in, user=user)


def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]


def sort_rank(vote: models.RankedChoiceVotes):
    return vote.rank


def dupcheck(x):
    for elem in x:
        if x.count(elem) > 1:
            return True
        return False
