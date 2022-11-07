from quart import Blueprint, render_template, request, abort
from quart_discord import requires_authorization
import tortoise.exceptions

from alttprbot import models

from ..api import discord

# TODO: add a way to resubmit votes (low priority)
# TODO: add verification that the user is authorized to vote
# TODO: client-side verification that ranked choices are unique
# TODO: the entire Discord-side of this need to be written

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

    await election.fetch_related('candidates')

    existing_votes = await election.votes.filter(user_id=user.id)
    if existing_votes:
        await abort(403, "You have already voted in this election.  Please contact Synack if you need to change your vote.")

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

    await election.fetch_related('candidates')

    existing_votes = await election.votes.filter(user_id=user.id)
    if existing_votes:
        await abort(403, "You have already voted in this election.  Please contact Synack if you need to change your vote.")

    payload = await request.form

    if dupcheck(payload.values()):
        return await abort(400, "Each candidate must have a unique rank.")

    if dupcheck(payload.keys()):
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